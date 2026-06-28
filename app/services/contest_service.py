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
