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


async def _recover_stuck_submissions():
    """恢复卡死在 JUDGING 状态的提交（worker 崩溃后残留）。"""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Submission.id)
                .where(Submission.state == SubmissionState.JUDGING)
                .limit(10)
            )
            stuck = list(result.scalars().all())
            if stuck:
                logger.warning("发现 %d 个卡死的提交，重置为 QUEUED", len(stuck))
                for sid in stuck:
                    await db.execute(
                        update(Submission)
                        .where(Submission.id == sid)
                        .values(state=SubmissionState.QUEUED)
                    )
                await db.commit()
    except Exception as e:
        logger.error("恢复卡死提交失败: %s", e)


async def judge_worker(worker_id: int):
    """判题 worker — 独立轮询，原子认领提交"""
    logger.info("Worker-%d 启动", worker_id)
    poll_count = 0
    while True:
        try:
            # 每 10 次轮询（约 5 秒）检查一次卡死的提交
            poll_count += 1
            if poll_count % 10 == 0:
                await _recover_stuck_submissions()

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
            judging = Judging(
                submission_id=submission.id,
                result=Verdict.RTE,
                score=0.0,
                started=datetime.utcnow(),
                ended=datetime.utcnow(),
            )
            db.add(judging)
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

        # 题目无测试数据 — 无法判题
        if len(testcases) == 0:
            logger.warning("Judge: no testcases for problem %d, submission=%d", submission.problem_id, submission_id)
            judging = Judging(
                submission_id=submission.id,
                result=Verdict.RTE,
                score=0.0,
                started=datetime.utcnow(),
                ended=datetime.utcnow(),
            )
            db.add(judging)
            submission.state = SubmissionState.DONE
            await db.commit()
            return

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
                    # CE: 存储编译错误信息，让用户可以看到具体错误
                    judging.result = Verdict.CE
                    judging.ended = datetime.utcnow()
                    submission.state = SubmissionState.DONE
                    # 创建一条 JudgeRun 来保存编译错误详情
                    if testcases:
                        ce_run = JudgeRun(
                            judging_id=judging.id,
                            testcase_id=testcases[0].id,
                            result=Verdict.CE.value,
                            runtime=0.0,
                            output=compile_output or "(无编译输出)",
                        )
                        db.add(ce_run)
                    await db.commit()
                    return

            # ── 运行测试点 ──
            run_results = []
            ce_encountered = False
            for tc in testcases:
                # 如果已经遇到 CE（Docker模式），跳过剩余测试点
                if ce_encountered:
                    run = JudgeRun(
                        judging_id=judging.id,
                        testcase_id=tc.id,
                        result=Verdict.CE.value,
                        runtime=0.0,
                        output="(同上编译错误)",
                    )
                    db.add(run)
                    run_results.append((Verdict.CE.value, 0.0))
                    continue

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

                # Docker 模式下 CE 短路：第一个 CE 后跳过后续测试点
                if verdict == "CE" and settings.USE_DOCKER_SANDBOX:
                    ce_encountered = True
                    # 将编译错误信息保存到第一个 CE 测试点的 output 中
                    error_msg = stderr if stderr else "(编译错误，无详细信息)"

                # Log abnormal results for debugging
                if verdict in ("RTE", "CE", "MLE", "OLE"):
                    logger.warning(
                        "%s on testcase %d: stderr=%s",
                        verdict, tc.id, stderr[:200] if stderr else "(empty)"
                    )

                # Only compare output if execution was normal (no verdict yet)
                if verdict is None:
                    verdict = compare_output(output, tc.output)

                # For CE in Docker mode, use the compiler error as output
                run_output = error_msg if (verdict == "CE" and settings.USE_DOCKER_SANDBOX) else output

                run = JudgeRun(
                    judging_id=judging.id,
                    testcase_id=tc.id,
                    result=verdict,
                    runtime=runtime,
                    output=run_output,
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

        except asyncio.CancelledError:
            # Worker 被取消（正常关闭）
            logger.info("Worker-%d 被取消，正在处理的 submission=%d 已回退为 QUEUED", worker_id, submission_id)
            if judging:
                judging.result = None
            submission.state = SubmissionState.QUEUED
            try:
                await db.commit()
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error("判题异常 submission=%d: %s", submission_id, e, exc_info=True)
            if judging:
                judging.result = Verdict.RTE
                judging.ended = datetime.utcnow()
                # 创建 JudgeRun 记录异常信息
                if testcases:
                    try:
                        err_run = JudgeRun(
                            judging_id=judging.id,
                            testcase_id=testcases[0].id,
                            result=Verdict.RTE.value,
                            runtime=0.0,
                            output=f"判题系统内部错误: {str(e)[:500]}",
                        )
                        db.add(err_run)
                    except Exception:
                        pass
            submission.state = SubmissionState.DONE
            try:
                await db.commit()
            except Exception:
                pass

        finally:
            if work_dir is not None:
                shutil.rmtree(work_dir, ignore_errors=True)


async def _update_scoreboard(db: AsyncSession, submission: Submission, verdict: str, score: float, contest: Contest):
    """更新计分板缓存 — 使用 upsert 防止竞态条件"""
    # 原子 upsert: INSERT OR UPDATE
    if is_postgresql():
        from sqlalchemy import text as sa_text
        await db.execute(sa_text("""
            INSERT INTO scoreboard (contest_id, team_id, problem_id, submissions, is_correct, score, total_time)
            VALUES (:cid, :tid, :pid, 1, :correct, :score, :ttime)
            ON CONFLICT (contest_id, team_id, problem_id) DO UPDATE SET
                submissions = scoreboard.submissions + 1,
                is_correct = CASE WHEN scoreboard.is_correct THEN TRUE ELSE :correct END,
                score = GREATEST(scoreboard.score, :score),
                total_time = CASE WHEN scoreboard.is_correct THEN scoreboard.total_time ELSE :ttime END
        """), {
            "cid": submission.contest_id, "tid": submission.team_id, "pid": submission.problem_id,
            "correct": verdict == Verdict.AC.value,
            "score": score,
            "ttime": _calc_penalty(submission, contest, verdict),
        })
        await db.commit()
        return

    # SQLite fallback: SELECT + INSERT/UPDATE
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
        entry.total_time = _calc_penalty(submission, contest, verdict)
    else:
        entry.score = max(entry.score, score)

    await db.commit()


def _calc_penalty(submission, contest, verdict) -> int:
    """计算 ICPC 罚时（分钟）"""
    if contest and verdict == Verdict.AC.value and submission.submit_time:
        elapsed = int((submission.submit_time - contest.start_time).total_seconds() / 60)
        return max(0, elapsed)
    return 0


async def _update_progress(db: AsyncSession, user_id: int, problem_id: int, verdict: str):
    """更新用户刷题进度 — 使用 upsert 防竞态"""
    from app.models import UserProgress
    is_ac = verdict == Verdict.AC.value
    now = datetime.utcnow()

    if is_postgresql():
        from sqlalchemy import text as sa_text
        await db.execute(sa_text("""
            INSERT INTO user_progress (user_id, problem_id, total_submissions, ac_count, first_ac_time)
            VALUES (:uid, :pid, 1, :ac, :fat)
            ON CONFLICT (user_id, problem_id) DO UPDATE SET
                total_submissions = user_progress.total_submissions + 1,
                ac_count = user_progress.ac_count + :ac_inc,
                first_ac_time = COALESCE(user_progress.first_ac_time, :fat)
        """), {
            "uid": user_id, "pid": problem_id,
            "ac": 1 if is_ac else 0,
            "ac_inc": 1 if is_ac else 0,
            "fat": now if is_ac else None,
        })
        await db.commit()
        return

    # SQLite fallback
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
    if is_ac:
        prog.ac_count += 1
        if prog.first_ac_time is None:
            prog.first_ac_time = now
    await db.commit()
