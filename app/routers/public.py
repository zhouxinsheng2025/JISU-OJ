from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Contest
from app.services import score_service
from app.templates_helpers import templates

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/scoreboard")
async def public_scoreboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    contest_id: int = Query(None),
):
    from datetime import datetime, timezone

    if contest_id:
        result = await db.execute(select(Contest).where(Contest.id == contest_id))
    else:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Contest)
            .where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now)
            .limit(1)
        )
    contest = result.scalar_one_or_none()

    if contest is None:
        return templates.TemplateResponse(
            "public/scoreboard.html",
            {"request": request, "contest": None, "board": [], "problems": [], "freeze": False},
        )

    now = datetime.now(timezone.utc)
    freeze = contest.freeze_time is not None and now >= contest.freeze_time
    board = await score_service.get_scoreboard(db, contest.id, freeze=freeze, freeze_time=contest.freeze_time)
    problems = await score_service.get_contest_problems(db, contest.id)
    return templates.TemplateResponse(
        "public/scoreboard.html",
        {"request": request, "contest": contest, "board": board, "problems": problems, "freeze": freeze},
    )
