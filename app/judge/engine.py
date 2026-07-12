"""
判题引擎 — 多 worker 并行架构

架构:
  asyncio.create_task(judge_worker(0))
  asyncio.create_task(judge_worker(1))
  asyncio.create_task(judge_worker(2))
  └── 每个 worker 独立轮询 ──→ 原子认领提交 ──→ 判题

认领策略:
  PostgreSQL: SELECT ... FOR UPDATE SKIP LOCKED
  SQLite:     UPDATE + SELECT 在事务内原子完成
"""
import asyncio
import logging
import os
import shutil
import tempfile
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from app.config import settings
from app.database import async_session, is_postgresql
from app.models import (
    Submission, SubmissionState, Judging, JudgeRun, TestCase,
    Contest, Verdict, Problem, ScoreboardCache, ScoreMode,
    ContestProblem
)
from app.judge.compiler import compile_code
from app.judge.runner import run_program
from app.judge.scorer import compare_output, calculate_icpc_result, calculate_ioi_result

logger = logging.getLogger(__name__)

# WebSocket 订阅者列表
_subscribers: list[asyncio.Queue] = []


def subscribe() -> asyncio.Queue:
    """注册一个 WebSocket 订阅者，返回事件队列。"""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    """取消注册。"""
    if queue in _subscribers:
        _subscribers.remove(queue)


async def _publish(event: dict) -> None:
    """向所有订阅者广播事件。"""
    for queue in _subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def start_judge_engine():
    """启动判题引擎 — 创建多个并行 worker"""
    for i in range(settings.JUDGE_WORKERS):
        asyncio.create_task(judge_worker(i))
    logger.info("%d 个判题 worker 已启动", settings.JUDGE_WORKERS)


async def judge_worker(worker_id: int):
    """判题 worker — 独立轮询，原子认领提交"""
    logger.info("Worker-%d 启动", worker_id)
    while True:
        try:
            submission_id = await _claim_submission(worker_id)
            if submission_id:
                await _judge_submission(submission_id, worker_id)
            else:
                await asyncio.sleep(settings.JUDGE_POLL_INTERVAL)
        except Exception as e:
            logger.error("Worker-%d 错误: %s", worker_id, e, exc_info=True)
            await asyncio.sleep(settings.JUDGE_POLL_INTERVAL)


async def _claim_submission(worker_id: int) -> int | None:
    """原子认领一个 QUEUED 提交（防多 worker 抢占）"""
    async with async_session() as db:
        async with db.begin():
            if is_postgresql():
                # PostgreSQL: SELECT ... FOR UPDATE SKIP LOCKED
                result = await db.execute(
                    select(Submission.id)
                    .where(Submission.state == SubmissionState.QUEUED)
                    .order_by(Submission.submit_time.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                row = result.scalar_one_or_none()
                if row is None:
                    return None
                submission_id = row
                await db.execute(
                    update(Submission)
                    .where(Submission.id == submission_id)
                    .values(state=SubmissionState.JUDGING)
                )
            else:
                # SQLite: UPDATE + SELECT 在事务内原子完成
                # 先取一个 queued 的 id，再原子更新
                result = await db.execute(
                    select(Submission.id)
                    .where(Submission.state == SubmissionState.QUEUED)
                    .order_by(Submission.submit_time.asc())
                    .limit(1)
                )
                row = result.scalar_one_or_none()
                if row is None:
                    await db.rollback()
                    return None
                submission_id = row
                # 原子更新（事务内，其他 worker 会被阻塞或读到旧值）
                upd_result = await db.execute(
                    update(Submission)
                    .where(
                        Submission.id == submission_id,
                        Submission.state == SubmissionState.QUEUED
                    )
                    .values(state=SubmissionState.JUDGING)
                )
                if upd_result.rowcount == 0:
                    # 已被其他 worker 抢走
                    await db.rollback()
                    return None

            await db.commit()
            return submission_id


async def _judge_submission(submission_id: int, worker_id: int):
    """判题单个提交"""
    async with async_session() as db:
        result = await db.execute(
            select(Submission)
            .where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            return

        logger.debug("Judge start: submission=%d lang=%s prob=%d code_len=%d",
                     submission_id, submission.language,
                     submission.problem_id, len(submission.source_code))

        # 并行加载题目、测试数据、比赛信息
        problem_result = await db.execute(
            select(Problem).where(Problem.id == submission.problem_id)
        )
        problem = problem_result.scalar_one_or_none()
        if problem is None:
            logger.error("Judge: problem not found for submission %d", submission_id)
            submission.state = SubmissionState.DONE
            await db.commit()
            return

        tc_result = await db.execute(
            select(TestCase)
            .where(TestCase.problem_id == submission.problem_id)
            .order_by(TestCase.order)
        )
        testcases = list(tc_result.scalars().all())
        logger.debug("Judge: %d testcases for problem %d", len(testcases), submission.problem_id)

        contest_result = await db.execute(
            select(Contest).where(Contest.id == submission.contest_id)
        )
        contest = contest_result.scalar_one_or_none()
        score_mode = contest.score_mode.value if contest else "icpc"

        # 工作目录（仅 subprocess 模式使用）
        work_dir = None
        if not settings.USE_DOCKER_SANDBOX:
            work_dir = tempfile.mkdtemp(dir=settings.RUNS_DIR)
            os.makedirs(work_dir, exist_ok=True)

        judging = None
        try:
            judging = Judging(
                submission_id=submission.id,
                started=datetime.utcnow(),
            )
            db.add(judging)
            await db.flush()

            # ── 编译 ──
            # Docker 沙箱模式：编译在容器内完成（与运行一起）
            # Subprocess 模式：在外部编译一次，然后逐测试点运行
            exe_or_error = None
            compile_ok = True

            if not settings.USE_DOCKER_SANDBOX:
                compile_ok, exe_or_error, compile_output = await compile_code(
                    submission.source_code, submission.language, work_dir
                )
                if not compile_ok:
                    judging.result = Verdict.CE
                    judging.ended = datetime.utcnow()
                    submission.state = SubmissionState.DONE
                    await db.commit()
                    return

            # ── 运行测试点 ──
            run_results = []
            for tc in testcases:
                if settings.USE_DOCKER_SANDBOX:
                    # Docker sandbox: compile + run in isolated container
                    from app.judge.sandbox import run_in_container
                    verdict, output, runtime, stderr = await run_in_container(
                        submission.language, submission.source_code,
                        tc.input, problem.time_limit, problem.memory_limit,
                    )
                else:
                    # Subprocess runner: run pre-compiled binary
                    verdict, output, runtime, stderr = await run_program(
                        exe_or_error, submission.language, work_dir,
                        tc.input, problem.time_limit, problem.memory_limit,
                    )

                # Log abnormal results for debugging
                if verdict in ("RTE", "CE", "MLE", "OLE"):
                    logger.warning(
                        "%s on testcase %d: stderr=%s",
                        verdict, tc.id, stderr[:200] if stderr else "(empty)"
                    )

                # Only compare output if execution was normal (no verdict yet)
                if verdict is None:
                    verdict = compare_output(output, tc.output)

                run = JudgeRun(
                    judging_id=judging.id,
                    testcase_id=tc.id,
                    result=verdict,
                    runtime=runtime,
                    output=output,
                )
                db.add(run)
                run_results.append((verdict, runtime))

            # 汇总
            logger.debug("Judge run_results: %s", [(v, round(t, 3)) for v, t in run_results])
            if score_mode == "ioi":
                final_verdict, final_score = calculate_ioi_result(run_results, len(testcases))
            else:
                final_verdict, _ = calculate_icpc_result(run_results)
                final_score = 100.0 if final_verdict == Verdict.AC.value else 0.0
            logger.info("Judge done: submission=%d verdict=%s score=%.1f",
                        submission_id, final_verdict, final_score)

            judging.result = final_verdict
            judging.score = final_score
            judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            await db.commit()

            # 更新计分板 + 用户进度
            await _update_scoreboard(db, submission, final_verdict, final_score, contest)
            await _update_progress(db, submission.team_id, submission.problem_id, final_verdict)

            # 通知 WebSocket 订阅者
            await _publish({
                "type": "judging_done",
                "submission_id": submission.id,
                "team_id": submission.team_id,
                "problem_id": submission.problem_id,
                "verdict": final_verdict,
                "score": final_score,
            })

        except Exception as e:
            logger.error("判题失败 submission=%d: %s", submission_id, e, exc_info=True)
            if judging:
                judging.result = Verdict.RTE
                judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            try:
                await db.commit()
            except Exception:
                pass

        finally:
            if work_dir is not None:
                shutil.rmtree(work_dir, ignore_errors=True)


async def _update_scoreboard(db: AsyncSession, submission: Submission, verdict: str, score: float, contest: Contest):
    """更新计分板缓存"""
    result = await db.execute(
        select(ScoreboardCache).where(
            ScoreboardCache.contest_id == submission.contest_id,
            ScoreboardCache.team_id == submission.team_id,
            ScoreboardCache.problem_id == submission.problem_id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = ScoreboardCache(
            contest_id=submission.contest_id,
            team_id=submission.team_id,
            problem_id=submission.problem_id,
        )
        db.add(entry)

    entry.submissions += 1

    if verdict == Verdict.AC.value:
        if entry.is_correct:
            await db.commit()
            return
        entry.is_correct = True
        entry.score = max(entry.score, score)
        if contest:
            elapsed = int((submission.submit_time - contest.start_time).total_seconds() / 60)
            entry.total_time = elapsed + (entry.submissions - 1) * 20
    else:
        entry.score = max(entry.score, score)

    await db.commit()


async def _update_progress(db: AsyncSession, user_id: int, problem_id: int, verdict: str):
    """更新用户刷题进度"""
    from app.models import UserProgress
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.problem_id == problem_id,
        )
    )
    prog = result.scalar_one_or_none()
    if prog is None:
        prog = UserProgress(user_id=user_id, problem_id=problem_id)
        db.add(prog)

    prog.total_submissions += 1
    if verdict == Verdict.AC.value:
        prog.ac_count += 1
        if prog.first_ac_time is None:
            prog.first_ac_time = datetime.utcnow()
    await db.commit()
