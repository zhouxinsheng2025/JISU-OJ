from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest
from app.schemas import ContestCreate
from app.services import contest_service
from app.services import score_service
from app.templates_helpers import templates

router = APIRouter(prefix="/jury", tags=["jury"])

TEMPLATE_DIR = "jury"


# ── 计分板 ──
@router.get("/scoreboard")
async def jury_scoreboard(
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
    contest_id: int = Query(None),
):
    from datetime import datetime

    if contest_id is None:
        # 默认显示第一个启用的比赛
        result = await db.execute(select(Contest).where(Contest.enabled == True).order_by(Contest.id.desc()).limit(1))
        contest = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Contest).where(Contest.id == contest_id))
        contest = result.scalar_one_or_none()

    if contest is None:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/dashboard.html",
            {"request": request, "user": user, "error": "没有比赛"},
        )

    board = await score_service.get_scoreboard(db, contest.id, freeze=False)  # Jury 永远看真实排名
    problems = await score_service.get_contest_problems(db, contest.id)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/scoreboard.html",
        {"request": request, "user": user, "contest": contest, "board": board, "problems": problems},
    )


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


# ── 题目列表 ──
@router.get("/contests/{contest_id}/problems")
async def list_problems(contest_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    from sqlalchemy import select
    from app.models import Problem
    result = await db.execute(
        select(Problem).where(Problem.contest_id == contest_id).order_by(Problem.order)
    )
    problems = list(result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problems.html",
        {"request": request, "user": user, "contest": contest, "problems": problems},
    )


# ── 创建题目 ──
@router.get("/contests/{contest_id}/problems/new")
async def new_problem_page(contest_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problem_form.html",
        {"request": request, "user": user, "contest": contest, "problem": None},
    )


@router.post("/contests/{contest_id}/problems/new")
async def create_problem(
    contest_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    order: int = Form(0),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Problem
    problem = Problem(
        contest_id=contest_id,
        title=title,
        description=description,
        time_limit=time_limit,
        memory_limit=memory_limit,
        order=order,
    )
    db.add(problem)
    await db.commit()
    return RedirectResponse(url=f"/jury/contests/{contest_id}/problems", status_code=303)


# ── 编辑题目 ──
@router.get("/problems/{problem_id}/edit")
async def edit_problem_page(problem_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models import Problem
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    contest = await contest_service.get_contest(db, problem.contest_id)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problem_form.html",
        {"request": request, "user": user, "contest": contest, "problem": problem},
    )


@router.post("/problems/{problem_id}/edit")
async def edit_problem(
    problem_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    order: int = Form(0),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models import Problem
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    problem.title = title
    problem.description = description
    problem.time_limit = time_limit
    problem.memory_limit = memory_limit
    problem.order = order
    await db.commit()
    return RedirectResponse(url=f"/jury/contests/{problem.contest_id}/problems", status_code=303)


# ── 测试数据管理 ──
@router.get("/problems/{problem_id}/testcases")
async def manage_testcases(problem_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models import Problem, TestCase
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    tc_result = await db.execute(
        select(TestCase).where(TestCase.problem_id == problem_id).order_by(TestCase.order)
    )
    testcases = list(tc_result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/testcases.html",
        {"request": request, "user": user, "problem": problem, "testcases": testcases},
    )


@router.post("/problems/{problem_id}/testcases/new")
async def add_testcase(
    problem_id: int,
    request: Request,
    input_data: str = Form("", alias="input"),
    output_data: str = Form("", alias="output"),
    is_sample: str = Form("0"),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import TestCase
    tc = TestCase(
        problem_id=problem_id,
        input=input_data,
        output=output_data,
        is_sample=(is_sample == "1"),
    )
    db.add(tc)
    await db.commit()
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)


@router.post("/problems/{problem_id}/testcases/delete/{tc_id}")
async def delete_testcase(problem_id: int, tc_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models import TestCase
    result = await db.execute(select(TestCase).where(TestCase.id == tc_id, TestCase.problem_id == problem_id))
    tc = result.scalar_one_or_none()
    if tc:
        await db.delete(tc)
        await db.commit()
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)
