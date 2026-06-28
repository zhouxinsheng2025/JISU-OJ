from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ScoreboardCache, Contest, User, ScoreMode, Problem, ContestProblem


async def get_scoreboard(db: AsyncSession, contest_id: int, freeze: bool = False):
    """获取计分板数据，freeze=True 时冻结排名（不显示封榜后的提交结果）"""
    result = await db.execute(
        select(ScoreboardCache).where(ScoreboardCache.contest_id == contest_id)
    )
    entries = list(result.scalars().all())

    # 按队伍分组
    team_stats = {}
    for e in entries:
        if e.team_id not in team_stats:
            team_stats[e.team_id] = {"solved": 0, "total_time": 0, "total_score": 0.0, "problems": {}}
        team_stats[e.team_id]["problems"][e.problem_id] = e
        if e.is_correct:
            team_stats[e.team_id]["solved"] += 1
            team_stats[e.team_id]["total_time"] += e.total_time
        team_stats[e.team_id]["total_score"] += e.score

    # 获取队伍名
    team_ids = list(team_stats.keys())
    if team_ids:
        user_result = await db.execute(select(User).where(User.id.in_(team_ids)))
        users = {u.id: u for u in user_result.scalars().all()}
    else:
        users = {}

    # 构建排序后的计分板
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

    contest_result = await db.execute(select(Contest).where(Contest.id == contest_id))
    contest = contest_result.scalar_one_or_none()

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
