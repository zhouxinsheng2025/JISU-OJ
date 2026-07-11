from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Contest, ContestProblem, Problem
from app.schemas import ContestCreate


async def create_contest(db: AsyncSession, data: ContestCreate) -> Contest:
    contest = Contest(
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        score_mode=data.score_mode,
        ctype=data.ctype,
        freeze_time=data.freeze_time,
    )
    db.add(contest)
    await db.commit()
    await db.refresh(contest)
    return contest


async def get_contests(db: AsyncSession) -> list[Contest]:
    result = await db.execute(select(Contest).order_by(Contest.id.desc()))
    return list(result.scalars().all())


async def get_contest(db: AsyncSession, contest_id: int) -> Contest | None:
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    return result.scalar_one_or_none()


async def update_contest(db: AsyncSession, contest_id: int, data: ContestCreate) -> Contest | None:
    contest = await get_contest(db, contest_id)
    if contest is None:
        return None
    contest.title = data.title
    contest.start_time = data.start_time
    contest.end_time = data.end_time
    contest.score_mode = data.score_mode
    contest.ctype = data.ctype
    contest.freeze_time = data.freeze_time
    await db.commit()
    await db.refresh(contest)
    return contest


async def toggle_contest(db: AsyncSession, contest_id: int) -> Contest | None:
    contest = await get_contest(db, contest_id)
    if contest is None:
        return None
    contest.enabled = not contest.enabled
    await db.commit()
    return contest


async def delete_contest(db: AsyncSession, contest_id: int) -> bool:
    contest = await get_contest(db, contest_id)
    if contest is None:
        return False
    # 级联删除关联数据: ContestProblem, ScoreboardCache, 提交及判题, 问答
    from app.models import ContestProblem, ScoreboardCache, Submission, Judging, JudgeRun, Clarification
    from sqlalchemy import delete

    # 1. 删除 ContestProblem 关联
    await db.execute(delete(ContestProblem).where(ContestProblem.contest_id == contest_id))
    # 2. 删除计分板缓存
    await db.execute(delete(ScoreboardCache).where(ScoreboardCache.contest_id == contest_id))
    # 3. 删除问答
    await db.execute(delete(Clarification).where(Clarification.contest_id == contest_id))
    # 4. 删除提交的判题记录 + 提交本身
    sub_result = await db.execute(
        select(Submission.id).where(Submission.contest_id == contest_id)
    )
    sub_ids = [row[0] for row in sub_result.all()]
    for sid in sub_ids:
        j_result = await db.execute(select(Judging.id).where(Judging.submission_id == sid))
        for j_row in j_result.all():
            await db.execute(delete(JudgeRun).where(JudgeRun.judging_id == j_row[0]))
        await db.execute(delete(Judging).where(Judging.submission_id == sid))
    await db.execute(delete(Submission).where(Submission.contest_id == contest_id))
    # 5. 删除比赛
    await db.delete(contest)
    await db.commit()
    return True


# ── Problem Bank / ContestProblem management ──


async def get_problems(db: AsyncSession, contest_id: int) -> list[Problem]:
    """Get problems for a contest through ContestProblem join."""
    result = await db.execute(
        select(Problem)
        .join(ContestProblem, ContestProblem.problem_id == Problem.id)
        .where(ContestProblem.contest_id == contest_id)
        .order_by(ContestProblem.order)
    )
    return list(result.scalars().all())


async def add_problem_to_contest(db: AsyncSession, contest_id: int, problem_id: int, order: int = 0) -> ContestProblem:
    cp = ContestProblem(contest_id=contest_id, problem_id=problem_id, order=order)
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return cp


async def remove_problem_from_contest(db: AsyncSession, contest_id: int, problem_id: int) -> bool:
    result = await db.execute(
        select(ContestProblem).where(
            ContestProblem.contest_id == contest_id,
            ContestProblem.problem_id == problem_id,
        )
    )
    cp = result.scalar_one_or_none()
    if cp is None:
        return False
    await db.delete(cp)
    await db.commit()
    return True


async def get_all_problems(db: AsyncSession) -> list[Problem]:
    """Get all problems from the problem bank."""
    result = await db.execute(select(Problem).order_by(Problem.id.desc()))
    return list(result.scalars().all())
