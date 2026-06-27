from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest
from app.schemas import ContestCreate
from app.services import contest_service
from app.templates_helpers import templates

router = APIRouter(prefix="/jury", tags=["jury"])

TEMPLATE_DIR = "jury"


# ── Dashboard ──
@router.get("/")
async def dashboard(request: Request, user: User = Depends(require_role("jury"))):
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/dashboard.html",
        {"request": request, "user": user},
    )


# ── 比赛列表 ──
@router.get("/contests")
async def list_contests(request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contests = await contest_service.get_contests(db)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/contests.html",
        {"request": request, "user": user, "contests": contests},
    )


# ── 创建比赛 ──
@router.get("/contests/new")
async def new_contest_page(request: Request, user: User = Depends(require_role("jury"))):
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/contest_form.html",
        {"request": request, "user": user, "contest": None},
    )


@router.post("/contests/new")
async def create_contest_action(
    request: Request,
    title: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    score_mode: str = Form("icpc"),
    freeze_time: str = Form(""),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    data = ContestCreate(
        title=title,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        score_mode=score_mode,
        freeze_time=datetime.fromisoformat(freeze_time) if freeze_time else None,
    )
    await contest_service.create_contest(db, data)
    return RedirectResponse(url="/jury/contests", status_code=303)


# ── 编辑比赛 ──
@router.get("/contests/{contest_id}/edit")
async def edit_contest_page(contest_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/contest_form.html",
        {"request": request, "user": user, "contest": contest},
    )


@router.post("/contests/{contest_id}/edit")
async def edit_contest_action(
    contest_id: int,
    request: Request,
    title: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    score_mode: str = Form("icpc"),
    freeze_time: str = Form(""),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    data = ContestCreate(
        title=title,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        score_mode=score_mode,
        freeze_time=datetime.fromisoformat(freeze_time) if freeze_time else None,
    )
    await contest_service.update_contest(db, contest_id, data)
    return RedirectResponse(url="/jury/contests", status_code=303)


# ── 启用/禁用比赛 ──
@router.post("/contests/{contest_id}/toggle")
async def toggle_contest_action(contest_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    await contest_service.toggle_contest(db, contest_id)
    return RedirectResponse(url="/jury/contests", status_code=303)


# ── 队伍列表 ──
@router.get("/teams")
async def list_teams(request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models import UserRole
    result = await db.execute(
        select(User).where(User.role == UserRole.TEAM).order_by(User.id)
    )
    teams = list(result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/teams.html",
        {"request": request, "user": user, "teams": teams},
    )


# ── 创建队伍 ──
@router.get("/teams/new")
async def new_team_page(request: Request, user: User = Depends(require_role("jury"))):
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/team_form.html",
        {"request": request, "user": user, "team": None},
    )


@router.post("/teams/new")
async def create_team(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    teamname: str = Form(...),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth_service import hash_password
    from app.models import UserRole
    team = User(
        username=username,
        password_hash=hash_password(password),
        teamname=teamname,
        role=UserRole.TEAM,
    )
    db.add(team)
    await db.commit()
    return RedirectResponse(url="/jury/teams", status_code=303)


# ── 编辑队伍 ──
@router.get("/teams/{team_id}/edit")
async def edit_team_page(team_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        return RedirectResponse(url="/jury/teams", status_code=303)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/team_form.html",
        {"request": request, "user": user, "team": team},
    )


@router.post("/teams/{team_id}/edit")
async def edit_team(
    team_id: int,
    request: Request,
    username: str = Form(...),
    password: str = Form(""),
    teamname: str = Form(...),
    enabled: str = Form("1"),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        return RedirectResponse(url="/jury/teams", status_code=303)
    team.username = username
    team.teamname = teamname
    team.enabled = (enabled == "1")
    if password:
        from app.services.auth_service import hash_password
        team.password_hash = hash_password(password)
    await db.commit()
    return RedirectResponse(url="/jury/teams", status_code=303)
