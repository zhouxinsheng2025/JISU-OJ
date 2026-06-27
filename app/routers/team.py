from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest, Problem, TestCase, Submission, Judging, Verdict
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
