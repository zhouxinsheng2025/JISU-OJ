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


# ── 删除比赛 ──
@router.post("/contests/{contest_id}/delete")
async def delete_contest_action(contest_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    await contest_service.delete_contest(db, contest_id)
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


# ── 删除队伍 ──
@router.post("/teams/{team_id}/delete")
async def delete_team(team_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == team_id))
    team = result.scalar_one_or_none()
    if team:
        await db.delete(team)
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
    await db.refresh(problem)
    return RedirectResponse(url=f"/jury/problems/{problem.id}/testcases", status_code=303)


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


# ── ZIP批量上传测试数据 ──
@router.post("/problems/{problem_id}/testcases/zip")
async def upload_testdata_zip(
    problem_id: int,
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import UploadFile, File
    from app.services.testcase_service import import_testcases_from_zip
    form = await request.form()
    file: UploadFile = form.get("zipfile")
    replace = form.get("replace", "0") == "1"
    if file and file.filename and file.filename.endswith('.zip'):
        content = await file.read()
        count = await import_testcases_from_zip(db, problem_id, content, replace=replace)
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)


@router.post("/problems/{problem_id}/testcases/delete/{tc_id}")
async def delete_testcase(problem_id: int, tc_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models import TestCase
    tc_result = await db.execute(select(TestCase).where(TestCase.id == tc_id))
    tc = tc_result.scalar_one_or_none()
    if tc:
        await db.delete(tc)
        await db.commit()
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)


# ── 澄清系统 ──

@router.get("/clarifications")
async def jury_clarifications(
    request: Request,
    contest_id: int = None,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Clarification
    from sqlalchemy.orm import joinedload

    if contest_id:
        clar_result = await db.execute(
            select(Clarification)
            .options(joinedload(Clarification.sender))
            .where(Clarification.contest_id == contest_id)
            .order_by(Clarification.created_at.desc())
        )
    else:
        clar_result = await db.execute(
            select(Clarification)
            .options(joinedload(Clarification.sender))
            .order_by(Clarification.created_at.desc())
        )
    clarifications = list(clar_result.unique().scalars().all())

    # 获取所有相关接收者用户
    user_ids = set()
    for c in clarifications:
        user_ids.add(c.sender_id)
        if c.recipient_id:
            user_ids.add(c.recipient_id)
    users_map = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in user_result.scalars().all()}

    # 获取比赛列表供筛选
    from app.services import contest_service
    contests = await contest_service.get_contests(db)

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/clarifications.html",
        {
            "request": request,
            "user": user,
            "clarifications": clarifications,
            "users_map": users_map,
            "contests": contests,
            "selected_contest_id": contest_id,
        },
    )


# ── 提交管理 ──

@router.get("/submissions")
async def jury_submissions(
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Submission, Judging

    result = await db.execute(
        select(Submission).order_by(Submission.submit_time.desc()).limit(100)
    )
    submissions = list(result.scalars().all())

    # 加载判题结果和关联信息
    sub_data = []
    for sub in submissions:
        j_result = await db.execute(
            select(Judging)
            .where(Judging.submission_id == sub.id)
            .order_by(Judging.id.desc())
        )
        jud = j_result.scalar_one_or_none()
        # 确保 team 和 problem 已加载
        await db.refresh(sub, ["team", "problem"])
        sub_data.append({"submission": sub, "judging": jud})

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submissions.html",
        {"request": request, "user": user, "submission_data": sub_data},
    )


@router.get("/submissions/{submission_id}")
async def jury_submission_detail(
    submission_id: int,
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Submission, Judging, JudgeRun

    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        return RedirectResponse(url="/jury/submissions", status_code=303)

    # 加载关联数据
    await db.refresh(sub, ["team", "problem"])

    # 加载判题和运行详情
    j_result = await db.execute(
        select(Judging)
        .where(Judging.submission_id == submission_id)
        .order_by(Judging.id.desc())
    )
    judging = j_result.scalar_one_or_none()

    runs = []
    if judging:
        runs_result = await db.execute(
            select(JudgeRun).where(JudgeRun.judging_id == judging.id)
        )
        runs = list(runs_result.scalars().all())

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submission_detail.html",
        {
            "request": request,
            "user": user,
            "submission": sub,
            "judging": judging,
            "runs": runs,
        },
    )


@router.post("/submissions/{submission_id}/rejudge")
async def rejudge_submission(
    submission_id: int,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Submission, SubmissionState, Judging, JudgeRun

    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if sub:
        # 收集所有关联的 judgeruns 并删除
        j_result = await db.execute(
            select(Judging).where(Judging.submission_id == submission_id)
        )
        judgings_list = j_result.scalars().all()
        for judging in judgings_list:
            runs_result = await db.execute(
                select(JudgeRun).where(JudgeRun.judging_id == judging.id)
            )
            for run in runs_result.scalars().all():
                await db.delete(run)
            await db.delete(judging)
        sub.state = SubmissionState.QUEUED
        await db.commit()
    return RedirectResponse(
        url=f"/jury/submissions/{submission_id}", status_code=303
    )


@router.post("/clarifications/{clar_id}/reply")
async def jury_reply(
    clar_id: int,
    answer: str = Form(...),
    make_public: str = Form("0"),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Clarification
    result = await db.execute(select(Clarification).where(Clarification.id == clar_id))
    clar = result.scalar_one_or_none()
    if clar:
        clar.answer = answer
        if make_public == "1":
            clar.recipient_id = None
        else:
            clar.recipient_id = user.id
        await db.commit()
    contest_param = f"?contest_id={clar.contest_id}" if clar else ""
    return RedirectResponse(url=f"/jury/clarifications{contest_param}", status_code=303)
