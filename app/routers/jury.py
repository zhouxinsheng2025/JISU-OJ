import io
from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest, Problem, ContestProblem, UserRole, Difficulty
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


# ── 导出成绩 ──
@router.get("/scoreboard/{contest_id}/export")
async def export_scoreboard(
    contest_id: int,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import StreamingResponse
    from app.services.export_service import export_contest_excel

    excel_bytes = await export_contest_excel(db, contest_id)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=contest_{contest_id}_results.xlsx"},
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
    ctype: str = Form("contest"),
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
        ctype=ctype,
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
    ctype: str = Form("contest"),
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
        ctype=ctype,
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
    team = User(
        username=username,
        password_hash=hash_password(password),
        teamname=teamname,
        role=UserRole.TEAM,
    )
    db.add(team)
    await db.commit()
    return RedirectResponse(url="/jury/teams", status_code=303)


# ── CSV批量导入队伍 ──
@router.post("/teams/csv")
async def import_teams_csv(
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    """批量导入队伍，CSV列: username,password,teamname"""
    from app.services.auth_service import hash_password
    form = await request.form()
    file: UploadFile = form.get("csvfile")
    if file is None or not file.filename:
        return RedirectResponse(url="/jury/teams", status_code=303)

    content = (await file.read()).decode("utf-8-sig")
    imported = 0
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        username = parts[0].strip()
        password = parts[1].strip()
        teamname = parts[2].strip()
        if not username or not password or not teamname:
            continue
        # 检查是否已存在
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            continue
        team = User(
            username=username,
            password_hash=hash_password(password),
            teamname=teamname,
            role=UserRole.TEAM,
        )
        db.add(team)
        imported += 1
    if imported:
        await db.commit()
    return RedirectResponse(url="/jury/teams", status_code=303)


# ── 编辑队伍 ──
@router.get("/teams/{team_id}/edit")
async def edit_team_page(team_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
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
    from sqlalchemy import delete
    from app.models import Submission, Judging, JudgeRun, Clarification, ScoreboardCache, UserProgress
    result = await db.execute(select(User).where(User.id == team_id))
    team = result.scalar_one_or_none()
    if team:
        # 级联删除队伍的所有数据
        sub_result = await db.execute(select(Submission.id).where(Submission.team_id == team_id))
        for (sid,) in sub_result.all():
            jr = await db.execute(select(Judging.id).where(Judging.submission_id == sid))
            for (jid,) in jr.all():
                await db.execute(delete(JudgeRun).where(JudgeRun.judging_id == jid))
            await db.execute(delete(Judging).where(Judging.submission_id == sid))
        await db.execute(delete(Submission).where(Submission.team_id == team_id))
        await db.execute(delete(ScoreboardCache).where(ScoreboardCache.team_id == team_id))
        await db.execute(delete(Clarification).where(Clarification.sender_id == team_id))
        await db.execute(delete(UserProgress).where(UserProgress.user_id == team_id))
        await db.delete(team)
        await db.commit()
    return RedirectResponse(url="/jury/teams", status_code=303)


# ═══════════════════════════════════════════
# 题库 (Problem Bank)
# ═══════════════════════════════════════════

@router.get("/bank")
async def problem_bank(
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
    difficulty: str = Query(None),
    tag: str = Query(None),
):
    """题库列表，支持按难度和标签筛选"""
    query = select(Problem).order_by(Problem.id.desc())
    if difficulty:
        query = query.where(Problem.difficulty == difficulty)
    if tag:
        query = query.where(Problem.tags.contains(tag))
    result = await db.execute(query)
    problems = list(result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/bank.html",
        {
            "request": request,
            "user": user,
            "problems": problems,
            "filter_difficulty": difficulty or "",
            "filter_tag": tag or "",
            "difficulties": Difficulty,
        },
    )


@router.get("/bank/new")
async def new_bank_problem_page(request: Request, user: User = Depends(require_role("jury"))):
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/bank_form.html",
        {"request": request, "user": user, "problem": None},
    )


@router.post("/bank/new")
async def create_bank_problem(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    difficulty: str = Form("easy"),
    tags: str = Form(""),
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    # 自动生成 pid (加入4位随机字符防并发冲突)
    from datetime import datetime, timezone
    import secrets
    suffix = secrets.token_hex(2)  # 4 hex chars
    pid = f"P{datetime.now(timezone.utc).strftime('%y%m%d%H%M%S')}{suffix}"

    problem = Problem(
        pid=pid,
        title=title,
        description=description,
        difficulty=difficulty,
        tags=tags,
        time_limit=time_limit,
        memory_limit=memory_limit,
    )
    db.add(problem)
    await db.commit()
    return RedirectResponse(url="/jury/bank", status_code=303)


@router.get("/bank/{problem_id}/edit")
async def edit_bank_problem_page(
    problem_id: int,
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/bank", status_code=303)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/bank_form.html",
        {"request": request, "user": user, "problem": problem},
    )


@router.post("/bank/{problem_id}/edit")
async def edit_bank_problem(
    problem_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    difficulty: str = Form("easy"),
    tags: str = Form(""),
    time_limit: float = Form(1.0),
    memory_limit: int = Form(256),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/bank", status_code=303)
    problem.title = title
    problem.description = description
    problem.difficulty = difficulty
    problem.tags = tags
    problem.time_limit = time_limit
    problem.memory_limit = memory_limit
    await db.commit()
    return RedirectResponse(url="/jury/bank", status_code=303)


@router.post("/bank/{problem_id}/delete")
async def delete_bank_problem(
    problem_id: int,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem:
        await db.delete(problem)
        await db.commit()
    return RedirectResponse(url="/jury/bank", status_code=303)


# ── 洛谷/Hydro 格式题目导入 ──
@router.post("/bank/import-luogu")
async def import_luogu_problem(
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.luogu_import import import_from_luogu_zip
    form = await request.form()
    file = form.get("zipfile")
    if file and file.filename and file.filename.endswith('.zip'):
        content = await file.read()
        if len(content) > settings.UPLOAD_SIZE_LIMIT:
            return RedirectResponse(url="/jury/bank", status_code=303)
        problem = await import_from_luogu_zip(db, content)
        if problem:
            return RedirectResponse(url=f"/jury/problems/{problem.id}/testcases", status_code=303)
    return RedirectResponse(url="/jury/bank", status_code=303)


# ═══════════════════════════════════════════
# 比赛题目管理 (via ContestProblem)
# ═══════════════════════════════════════════

@router.get("/contests/{contest_id}/problems")
async def list_problems(contest_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    problems = await contest_service.get_problems(db, contest_id)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problems.html",
        {"request": request, "user": user, "contest": contest, "problems": problems},
    )


@router.get("/contests/{contest_id}/add-problem")
async def add_problem_to_contest_page(
    contest_id: int,
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    """从题库选题添加到比赛"""
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)

    # 获取题库中所有题目
    bank_result = await db.execute(select(Problem).order_by(Problem.id.desc()))
    all_problems = list(bank_result.scalars().all())

    # 获取已添加到比赛中的题目ID
    contest_problems = await contest_service.get_problems(db, contest_id)
    added_ids = {p.id for p in contest_problems}

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/add_problem.html",
        {
            "request": request,
            "user": user,
            "contest": contest,
            "all_problems": all_problems,
            "added_ids": added_ids,
        },
    )


@router.post("/contests/{contest_id}/add-problem")
async def add_problem_to_contest_action(
    contest_id: int,
    request: Request,
    problem_id: int = Form(...),
    order: int = Form(0),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    await contest_service.add_problem_to_contest(db, contest_id, problem_id, order)
    return RedirectResponse(url=f"/jury/contests/{contest_id}/add-problem", status_code=303)


@router.post("/contests/{contest_id}/remove-problem")
async def remove_problem_from_contest_action(
    contest_id: int,
    request: Request,
    problem_id: int = Form(...),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    await contest_service.remove_problem_from_contest(db, contest_id, problem_id)
    return RedirectResponse(url=f"/jury/contests/{contest_id}/add-problem", status_code=303)


# ═══════════════════════════════════════════
# 测试数据管理 (standalone, no longer requires contest_id)
# ═══════════════════════════════════════════

@router.get("/problems/{problem_id}/testcases")
async def manage_testcases(problem_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from app.models import TestCase
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/jury/bank", status_code=303)
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


@router.post("/problems/{problem_id}/testcases/zip")
async def upload_testdata_zip(
    problem_id: int,
    request: Request,
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.testcase_service import import_testcases_from_zip
    form = await request.form()
    file: UploadFile = form.get("zipfile")
    replace = form.get("replace", "0") == "1"
    if file and file.filename and file.filename.endswith('.zip'):
        content = await file.read()
        await import_testcases_from_zip(db, problem_id, content, replace=replace)
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)


@router.post("/problems/{problem_id}/testcases/delete/{tc_id}")
async def delete_testcase(problem_id: int, tc_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
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

    user_ids = set()
    for c in clarifications:
        user_ids.add(c.sender_id)
        if c.recipient_id:
            user_ids.add(c.recipient_id)
    users_map = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in user_result.scalars().all()}

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
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.team),
            selectinload(Submission.problem),
            selectinload(Submission.judgings),
        )
        .order_by(Submission.submit_time.desc())
        .limit(100)
    )
    submissions = list(result.unique().scalars().all())

    sub_data = []
    for sub in submissions:
        # 取最新的一条判题记录（已经是关联加载的）
        judging = sub.judgings[-1] if sub.judgings else None
        sub_data.append({"submission": sub, "judging": judging})

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

    await db.refresh(sub, ["team", "problem"])

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
    from app.models import Submission, SubmissionState, Judging, JudgeRun, ScoreboardCache

    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if sub:
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
        # 清除计分板缓存，避免旧AC标记残留
        sb_result = await db.execute(
            select(ScoreboardCache).where(
                ScoreboardCache.contest_id == sub.contest_id,
                ScoreboardCache.team_id == sub.team_id,
                ScoreboardCache.problem_id == sub.problem_id,
            )
        )
        sb_entry = sb_result.scalar_one_or_none()
        if sb_entry:
            await db.delete(sb_entry)
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
