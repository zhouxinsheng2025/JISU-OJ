from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import (
    ScoreboardCache, Contest, User, ScoreMode, Problem, ContestProblem,
    Submission, Judging, Verdict, SubmissionState,
)


async def get_scoreboard(
    db: AsyncSession,
    contest_id: int,
    freeze: bool = False,
    freeze_time: datetime | None = None,
):
    """
    获取计分板数据。

    若 freeze=True 且 freeze_time 非空，则从原始提交数据重新计算封榜后的计分板，
    忽略 ScoreboardCache（因为缓存包含封榜之后的提交结果）。

    否则直接使用 ScoreboardCache 加速查询。
    """
    if freeze and freeze_time is not None:
        return await _build_frozen_board(db, contest_id, freeze_time)

    return await _build_cached_board(db, contest_id)


async def _build_cached_board(db: AsyncSession, contest_id: int):
    """从 ScoreboardCache 构建计分板（非封榜模式）。"""
    result = await db.execute(
        select(ScoreboardCache).where(ScoreboardCache.contest_id == contest_id)
    )
    entries = list(result.scalars().all())

    team_stats = _aggregate_entries(entries)
    contest = await _get_contest(db, contest_id)
    users = await _get_users(db, list(team_stats.keys()))

    return _render_board(team_stats, users, contest)


async def _build_frozen_board(
    db: AsyncSession,
    contest_id: int,
    freeze_time: datetime,
):
    """
    从原始提交数据重新计算封榜后的计分板。

    只统计 submit_time <= freeze_time 的提交，
    freeze_time 之后的提交被完全忽略。
    """
    contest = await _get_contest(db, contest_id)

    # 获取比赛中的所有题目
    problem_result = await db.execute(
        select(Problem)
        .join(ContestProblem, ContestProblem.problem_id == Problem.id)
        .where(ContestProblem.contest_id == contest_id)
    )
    problems = list(problem_result.scalars().all())
    problem_ids = {p.id for p in problems}

    # 查询封榜时间前的所有提交（带判题结果）
    sub_result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.judgings))
        .where(
            Submission.contest_id == contest_id,
            Submission.submit_time <= freeze_time,
            Submission.state == SubmissionState.DONE,
        )
        .order_by(Submission.submit_time.asc())
    )
    submissions = list(sub_result.unique().scalars().all())

    # 按 (team_id, problem_id) 逐对计算
    # key: (team_id, problem_id) -> {"submissions": int, "best": Judging, "first_ac_time": datetime}
    cell: dict[tuple[int, int], dict] = {}

    for sub in submissions:
        if sub.problem_id not in problem_ids:
            continue

        key = (sub.team_id, sub.problem_id)
        if key not in cell:
            cell[key] = {
                "submissions": 0,
                "best_judging": None,
                "best_score": 0.0,
                "is_correct": False,
                "first_ac_time": None,
            }
        entry = cell[key]
        entry["submissions"] += 1

        # 找到这个提交的最佳判题结果
        for j in (sub.judgings or []):
            score = j.score or 0.0
            if score > entry["best_score"]:
                entry["best_score"] = score
                entry["best_judging"] = j
            if j.result == Verdict.AC and not entry["is_correct"]:
                entry["is_correct"] = True
                entry["first_ac_time"] = sub.submit_time

    # 构建类似 ScoreboardCache 的 entries 对象
    # 使用一个简单的命名元组或手动构建
    class FrozenEntry:
        def __init__(self, team_id, problem_id, submissions, total_time, is_correct, score):
            self.team_id = team_id
            self.problem_id = problem_id
            self.submissions = submissions
            self.total_time = total_time
            self.is_correct = is_correct
            self.score = score

    entries = []
    for (team_id, problem_id), data in cell.items():
        # 计算罚时/总分
        if data["is_correct"] and contest:
            elapsed = int((data["first_ac_time"] - contest.start_time).total_seconds() / 60)
            total_time = max(0, elapsed) + (data["submissions"] - 1) * 20
        else:
            total_time = 0

        entries.append(FrozenEntry(
            team_id=team_id,
            problem_id=problem_id,
            submissions=data["submissions"],
            total_time=total_time,
            is_correct=data["is_correct"],
            score=data["best_score"],
        ))

    team_stats = _aggregate_entries(entries)
    users = await _get_users(db, list(team_stats.keys()))

    return _render_board(team_stats, users, contest)


# ── helper functions ──


def _aggregate_entries(entries):
    """按队伍聚合计分板条目。"""
    team_stats = {}
    for e in entries:
        if e.team_id not in team_stats:
            team_stats[e.team_id] = {
                "solved": 0, "total_time": 0, "total_score": 0.0, "problems": {},
            }
        team_stats[e.team_id]["problems"][e.problem_id] = e
        if e.is_correct:
            team_stats[e.team_id]["solved"] += 1
            team_stats[e.team_id]["total_time"] += e.total_time
        team_stats[e.team_id]["total_score"] += e.score
    return team_stats


async def _get_users(db: AsyncSession, team_ids: list[int]) -> dict[int, User]:
    """批量加载用户信息。"""
    if not team_ids:
        return {}
    user_result = await db.execute(select(User).where(User.id.in_(team_ids)))
    return {u.id: u for u in user_result.scalars().all()}


async def _get_contest(db: AsyncSession, contest_id: int) -> Contest | None:
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    return result.scalar_one_or_none()


def _render_board(team_stats: dict, users: dict[int, User], contest: Contest | None):
    """渲染最终计分板列表。"""
    board = []
    for team_id, stats in team_stats.items():
        user = users.get(team_id)
        board.append({
            "team_id": team_id,
            "teamname": user.teamname if user else f"Team {team_id}",
            "solved": stats["solved"],
            "total_time": stats["total_time"],
            "total_score": round(stats["total_score"], 2),
            "problems": stats["problems"],
        })

    if contest and contest.score_mode == ScoreMode.IOI:
        board.sort(key=lambda x: (-x["total_score"], x["total_time"]))
    else:
        board.sort(key=lambda x: (-x["solved"], x["total_time"]))

    return board


async def get_contest_problems(db: AsyncSession, contest_id: int):
    """Get problems for a contest through ContestProblem join table."""
    result = await db.execute(
        select(Problem)
        .join(ContestProblem, ContestProblem.problem_id == Problem.id)
        .where(ContestProblem.contest_id == contest_id)
        .order_by(ContestProblem.order)
    )
    return list(result.scalars().all())
