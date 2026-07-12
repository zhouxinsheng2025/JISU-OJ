from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import require_role
from app.models import (
    User, Contest, Problem, ContestProblem, TestCase,
    Submission, Judging, JudgeRun, Verdict, ContestType, UserProgress,
)
from app.templates_helpers import templates
from app.services import score_service

router = APIRouter(prefix="/team", tags=["team"])

TEMPLATE_DIR = "team"


async def _get_active_contest(db: AsyncSession) -> Contest | None:
    """Get current active contest (excluding practice)."""
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.ctype != ContestType.PRACTICE,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_or_create_practice_contest(db: AsyncSession) -> Contest | None:
    """Find the practice contest (开放练习)."""
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.ctype == ContestType.PRACTICE,
        ).order_by(Contest.id.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/")
async def dashboard(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    current_contest = result.scalar_one_or_none()

    # 检查是否有练习比赛
    practice = None
    if current_contest is None:
        practice = await _get_or_create_practice_contest(db)

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/dashboard.html",
        {
            "request": request,
            "user": user,
            "contest": current_contest,
            "practice": practice,
        },
    )


@router.get("/problems")
async def list_problems(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    contest = result.scalar_one_or_none()
    if contest is None:
        # Fall back to practice mode
        contest = await _get_or_create_practice_contest(db)
        if contest is None:
            return templates.TemplateResponse(
                f"{TEMPLATE_DIR}/dashboard.html",
                {"request": request, "user": user, "contest": None, "error": "当前没有进行中的比赛"},
            )

    # 通过 ContestProblem 查询题目
    prob_result = await db.execute(
        select(Problem)
        .join(ContestProblem, ContestProblem.problem_id == Problem.id)
        .where(ContestProblem.contest_id == contest.id)
        .order_by(ContestProblem.order)
    )
    problems = list(prob_result.scalars().all())

    # 查询本队伍每个题目的提交状态
    problem_ids = [p.id for p in problems]
    status_map = {}
    if problem_ids:
        sub_result = await db.execute(
            select(Submission.problem_id, Submission.state, Submission.id)
            .where(
                Submission.contest_id == contest.id,
                Submission.team_id == user.id,
                Submission.problem_id.in_(problem_ids),
            )
            .order_by(Submission.submit_time.desc())
        )
        rows = sub_result.all()
        attempted_set = {r[0] for r in rows}
        solved_set = set()
        if rows:
            sub_ids = [r[2] for r in rows]
            ac_result = await db.execute(
                select(Submission.problem_id)
                .join(Judging, Judging.submission_id == Submission.id)
                .where(
                    Submission.id.in_(sub_ids),
                    Judging.result == Verdict.AC,
                )
            )
            for row in ac_result.all():
                solved_set.add(row[0])

        for pid in problem_ids:
            if pid in solved_set:
                status_map[pid] = "solved"
            elif pid in attempted_set:
                status_map[pid] = "attempted"
            else:
                status_map[pid] = None

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problems.html",
        {
            "request": request,
            "user": user,
            "contest": contest,
            "problems": problems,
            "status_map": status_map,
        },
    )


@router.get("/problems/{problem_id}")
async def problem_detail(
    problem_id: int,
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/team/problems", status_code=303)

    tc_result = await db.execute(
        select(TestCase).where(
            TestCase.problem_id == problem_id, TestCase.is_sample == True
        ).order_by(TestCase.order)
    )
    samples = list(tc_result.scalars().all())

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problem_detail.html",
        {"request": request, "user": user, "problem": problem, "samples": samples},
    )


@router.post("/submit")
async def submit_code(
    request: Request,
    problem_id: int = Form(...),
    language: str = Form(...),
    source_code: str = Form(...),
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.services import submission_service

    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return {"error": "题目不存在"}

    now = datetime.utcnow()

    # 先查找本题目所属的进行中比赛
    cp_result = await db.execute(
        select(ContestProblem)
        .join(Contest, Contest.id == ContestProblem.contest_id)
        .where(
            ContestProblem.problem_id == problem_id,
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
            Contest.ctype != ContestType.PRACTICE,
        )
    )
    cp = cp_result.scalar_one_or_none()

    if cp is None:
        # 尝试练习模式 — 找练习比赛
        practice_contest = await _get_or_create_practice_contest(db)
        if practice_contest is None:
            return templates.TemplateResponse(
                f"{TEMPLATE_DIR}/problem_detail.html",
                {
                    "request": request,
                    "user": user,
                    "problem": problem,
                    "error": "该题目不在当前进行中的比赛中，且无练习比赛可用",
                },
            )
        contest_id = practice_contest.id
    else:
        contest_id = cp.contest_id

    if len(source_code) > 256 * 1024:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/problem_detail.html",
            {
                "request": request,
                "user": user,
                "problem": problem,
                "error": "代码超过256KB限制",
                "samples": [],
            },
        )

    valid_languages = {"c", "cpp", "python", "java"}
    if language not in valid_languages:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/problem_detail.html",
            {
                "request": request,
                "user": user,
                "problem": problem,
                "error": "不支持的语言类型",
                "samples": [],
            },
        )

    await submission_service.create_submission(
        db, contest_id, problem_id, user.id, language, source_code
    )
    return RedirectResponse(url="/team/submissions", status_code=303)


@router.get("/scoreboard")
async def team_scoreboard(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    contest = result.scalar_one_or_none()
    if contest is None:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/dashboard.html",
            {"request": request, "user": user, "contest": None, "error": "没有进行中的比赛"},
        )
    freeze = contest.freeze_time is not None and now >= contest.freeze_time
    board = await score_service.get_scoreboard(db, contest.id, freeze=freeze, freeze_time=contest.freeze_time)
    problems = await score_service.get_contest_problems(db, contest.id)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/scoreboard.html",
        {"request": request, "user": user, "contest": contest, "board": board, "problems": problems, "freeze": freeze},
    )


@router.get("/submissions")
async def my_submissions(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.services import submission_service

    submissions = await submission_service.get_team_submissions(db, user.id)

    submission_data = []
    for sub in submissions:
        # judgings 已通过 selectinload 预加载，无需额外查询
        judging = sub.judgings[-1] if sub.judgings else None
        submission_data.append({"submission": sub, "judging": judging})
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submissions.html",
        {"request": request, "user": user, "submission_data": submission_data},
    )


@router.get("/submissions/{submission_id}")
async def submission_detail(
    submission_id: int,
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.services import submission_service

    sub = await submission_service.get_submission_detail(db, submission_id)
    if sub is None or sub.team_id != user.id:
        return RedirectResponse(url="/team/submissions", status_code=303)

    judging_result = await db.execute(
        select(Judging)
        .where(Judging.submission_id == submission_id)
        .order_by(Judging.id.desc())
    )
    judging = judging_result.scalar_one_or_none()
    runs = []
    if judging:
        runs_result = await db.execute(
            select(JudgeRun)
            .options(selectinload(JudgeRun.testcase))
            .where(JudgeRun.judging_id == judging.id)
            .order_by(JudgeRun.id)
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


# ── 练习模式 ──

@router.get("/practice")
async def practice_dashboard(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    """练习模式首页 — 显示所有题库题目"""
    contest = await _get_or_create_practice_contest(db)
    if contest is None:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/dashboard.html",
            {"request": request, "user": user, "contest": None, "error": "练习模式未开启"},
        )

    prob_result = await db.execute(
        select(Problem)
        .join(ContestProblem, ContestProblem.problem_id == Problem.id)
        .where(ContestProblem.contest_id == contest.id)
        .order_by(ContestProblem.order)
    )
    problems = list(prob_result.scalars().all())

    # 查询练习进度
    progress_map = {}
    for p in problems:
        prog_result = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.problem_id == p.id,
            )
        )
        prog = prog_result.scalar_one_or_none()
        progress_map[p.id] = prog

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/practice.html",
        {
            "request": request,
            "user": user,
            "contest": contest,
            "problems": problems,
            "progress_map": progress_map,
        },
    )


# ── 澄清系统 ──

@router.get("/clarifications")
async def team_clarifications(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Clarification

    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    contest = result.scalar_one_or_none()

    clar_list = []
    if contest:
        from sqlalchemy.orm import joinedload
        clar_result = await db.execute(
            select(Clarification)
            .options(joinedload(Clarification.sender))
            .where(
                Clarification.contest_id == contest.id,
                ((Clarification.sender_id == user.id) | (Clarification.recipient_id == None))
            )
            .order_by(Clarification.created_at.desc())
        )
        clar_list = list(clar_result.unique().scalars().all())

    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/clarifications.html",
        {"request": request, "user": user, "contest": contest, "clarifications": clar_list},
    )


@router.post("/clarifications/new")
async def team_ask(
    request: Request,
    question: str = Form(...),
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Clarification

    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        ).limit(1)
    )
    contest = result.scalar_one_or_none()
    if contest is None:
        return RedirectResponse(url="/team/clarifications", status_code=303)

    clar = Clarification(contest_id=contest.id, sender_id=user.id, question=question)
    db.add(clar)
    await db.commit()
    return RedirectResponse(url="/team/clarifications", status_code=303)
