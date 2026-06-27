from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest, Problem, TestCase, Submission, Judging, JudgeRun, Verdict
from app.templates_helpers import templates

router = APIRouter(prefix="/team", tags=["team"])

TEMPLATE_DIR = "team"


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
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/dashboard.html",
        {"request": request, "user": user, "contest": current_contest},
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
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/dashboard.html",
            {"request": request, "user": user, "contest": None, "error": "当前没有进行中的比赛"},
        )

    prob_result = await db.execute(
        select(Problem).where(Problem.contest_id == contest.id).order_by(Problem.order)
    )
    problems = list(prob_result.scalars().all())

    # 查询本队伍每个题目的提交状态
    problem_ids = [p.id for p in problems]
    status_map = {}  # problem_id -> "solved" | "attempted" | None
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
        solved_set = set()
        attempted_set = set()
        for pid, _, sid in rows:
            attempted_set.add(pid)
        # 查出哪些提交获得了 AC
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

    # 获取样例测试数据
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

    # 验证题目存在
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return {"error": "题目不存在"}

    # 验证题目属于当前进行中的比赛
    now = datetime.utcnow()
    contest_result = await db.execute(
        select(Contest).where(
            Contest.id == problem.contest_id,
            Contest.enabled == True,
            Contest.start_time <= now,
            Contest.end_time >= now,
        )
    )
    contest = contest_result.scalar_one_or_none()
    if contest is None:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/problem_detail.html",
            {
                "request": request,
                "user": user,
                "problem": problem,
                "error": "该题目不在当前进行中的比赛中",
            },
        )

    # 检查源码大小
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

    # 校验语言
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
        db, problem.contest_id, problem_id, user.id, language, source_code
    )
    return RedirectResponse(url="/team/submissions", status_code=303)


@router.get("/submissions")
async def my_submissions(
    request: Request,
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from app.services import submission_service

    submissions = await submission_service.get_team_submissions(db, user.id)
    # 为每个提交加载最新判题结果
    from app.models import Judging

    submission_data = []
    for sub in submissions:
        j_result = await db.execute(
            select(Judging)
            .where(Judging.submission_id == sub.id)
            .order_by(Judging.id.desc())
        )
        judging = j_result.scalar_one_or_none()
        submission_data.append(
            {
                "submission": sub,
                "judging": judging,
            }
        )
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
