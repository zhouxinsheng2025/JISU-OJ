import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import async_session
from app.models import Submission, SubmissionState, Judging, JudgeRun, TestCase, Contest, Verdict, Problem, ScoreboardCache, ScoreMode
from app.judge.compiler import compile_code
from app.judge.runner import run_program
from app.judge.scorer import compare_output, calculate_icpc_result, calculate_ioi_result


async def judge_loop():
    """判题主循环，后台运行"""
    print("[Judge] 判题引擎已启动")
    while True:
        try:
            await _judge_pending()
        except Exception as e:
            print(f"[Judge] 错误: {e}")
        await asyncio.sleep(settings.JUDGE_POLL_INTERVAL)


async def _judge_pending():
    async with async_session() as db:
        # 取最早的 queued 提交
        result = await db.execute(
            select(Submission)
            .where(Submission.state == SubmissionState.QUEUED)
            .order_by(Submission.submit_time.asc())
            .limit(1)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            return

        # 标记为 judging
        submission.state = SubmissionState.JUDGING
        await db.commit()

    await _judge_submission(submission.id)


async def _judge_submission(submission_id: int):
    """判题单个提交"""
    async with async_session() as db:
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()
        if submission is None:
            return

        # 获取题目和测试数据
        problem_result = await db.execute(select(Problem).where(Problem.id == submission.problem_id))
        problem = problem_result.scalar_one_or_none()

        if problem is None:
            submission.state = SubmissionState.DONE
            await db.commit()
            return

        tc_result = await db.execute(
            select(TestCase).where(TestCase.problem_id == submission.problem_id).order_by(TestCase.order)
        )
        testcases = list(tc_result.scalars().all())

        # 获取比赛计分模式
        contest_result = await db.execute(select(Contest).where(Contest.id == submission.contest_id))
        contest = contest_result.scalar_one_or_none()
        score_mode = contest.score_mode.value if contest else "icpc"

        # 创建工作目录
        work_dir = tempfile.mkdtemp(dir=settings.RUNS_DIR)
        os.makedirs(work_dir, exist_ok=True)

        try:
            # 创建 Judging 记录
            judging = Judging(
                submission_id=submission.id,
                started=datetime.utcnow(),
            )
            db.add(judging)
            await db.flush()

            # 编译
            compile_ok, exe_or_error, compile_output = await compile_code(
                submission.source_code, submission.language, work_dir
            )
            if not compile_ok:
                judging.result = Verdict.CE
                judging.ended = datetime.utcnow()
                submission.state = SubmissionState.DONE
                await db.commit()
                # 写入编译错误到 judgerun（便于前端展示）
                run = JudgeRun(judging_id=judging.id, testcase_id=None, result=Verdict.CE, output=compile_output)
                db.add(run)
                await db.commit()
                return

            # 逐一运行测试点
            run_results = []
            for tc in testcases:
                verdict, output, runtime, stderr = await run_program(
                    exe_or_error, submission.language, work_dir,
                    tc.input, problem.time_limit, problem.memory_limit,
                )

                if verdict is None:
                    # 正常完成，比对输出
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

            # 汇总结果
            if score_mode == "ioi":
                final_verdict, final_score = calculate_ioi_result(run_results, len(testcases))
            else:
                final_verdict, max_runtime = calculate_icpc_result(run_results)
                final_score = 100.0 if final_verdict == Verdict.AC.value else 0.0

            judging.result = final_verdict
            judging.score = final_score
            judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            await db.commit()

            # 更新计分板缓存
            await _update_scoreboard(db, submission, final_verdict, final_score, contest)

        except Exception as e:
            judging.result = Verdict.RTE
            judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            run = JudgeRun(judging_id=judging.id, testcase_id=None, result=Verdict.RTE, output=str(e))
            db.add(run)
            await db.commit()

        finally:
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
            # Already AC — don't recompute penalty for subsequent submissions
            await db.commit()
            return
        entry.is_correct = True
        entry.score = max(entry.score, score)
        # 计算罚时：AC前的未通过提交*20 + 比赛开始到此次提交的分钟数
        elapsed = int((submission.submit_time - contest.start_time).total_seconds() / 60)
        entry.total_time = elapsed + (entry.submissions - 1) * 20
    else:
        entry.score = max(entry.score, score)

    await db.commit()
