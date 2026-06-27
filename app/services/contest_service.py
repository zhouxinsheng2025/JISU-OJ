from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Contest
from app.schemas import ContestCreate


async def create_contest(db: AsyncSession, data: ContestCreate) -> Contest:
    contest = Contest(
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        score_mode=data.score_mode,
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
