from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Submission, SubmissionState, Problem, Contest, Judging, JudgeRun


async def create_submission(
    db: AsyncSession,
    contest_id: int,
    problem_id: int,
    team_id: int,
    language: str,
    source_code: str,
) -> Submission:
    submission = Submission(
        contest_id=contest_id,
        problem_id=problem_id,
        team_id=team_id,
        language=language,
        source_code=source_code,
        submit_time=datetime.utcnow(),
        state=SubmissionState.QUEUED,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


async def get_team_submissions(db: AsyncSession, team_id: int) -> list[Submission]:
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.problem))
        .where(Submission.team_id == team_id)
        .order_by(Submission.submit_time.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_submission_detail(db: AsyncSession, submission_id: int) -> Submission | None:
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.problem))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        return None
    judging_result = await db.execute(
        select(Judging).where(Judging.submission_id == submission_id).order_by(Judging.id.desc())
    )
    submission._judgings = list(judging_result.scalars().all())
    return submission
