import pytest
from datetime import datetime, timedelta
from app.models import (
    Contest, Problem, ContestProblem, User, Submission, Judging, JudgeRun,
    SubmissionState, Verdict, ScoreMode, ContestType, UserRole, ScoreboardCache,
)
from app.services.score_service import get_scoreboard


async def seed_contest(db, score_mode="icpc"):
    """创建测试用比赛和题目。"""
    now = datetime.utcnow()
    contest = Contest(
        title="测试比赛",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        score_mode=score_mode,
        ctype=ContestType.CONTEST,
        enabled=True,
    )
    db.add(contest)
    await db.flush()

    problems = []
    for i in range(3):
        p = Problem(pid=f"P100{i+1}", title=f"题目{i+1}", time_limit=1.0, memory_limit=256)
        db.add(p)
        await db.flush()
        cp = ContestProblem(contest_id=contest.id, problem_id=p.id, order=i + 1)
        db.add(cp)
        problems.append(p)

    return contest, problems


async def seed_team(db, username="team1", teamname="队伍1"):
    from app.services.auth_service import hash_password
    user = User(
        username=username,
        password_hash=hash_password("123456"),
        teamname=teamname,
        role=UserRole.TEAM,
    )
    db.add(user)
    await db.flush()
    return user


async def seed_submission(db, contest_id, problem_id, team_id, verdict, submit_offset_min=0):
    """创建一条已完成判题的提交。"""
    now = datetime.utcnow()
    sub = Submission(
        contest_id=contest_id,
        problem_id=problem_id,
        team_id=team_id,
        language="python",
        source_code="print('hello')",
        submit_time=now - timedelta(minutes=submit_offset_min),
        state=SubmissionState.DONE,
    )
    db.add(sub)
    await db.flush()

    judging = Judging(
        submission_id=sub.id,
        result=verdict,
        score=100.0 if verdict == Verdict.AC else 0.0,
        started=now,
        ended=now,
    )
    db.add(judging)
    await db.flush()

    # 更新 ScoreboardCache
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(ScoreboardCache).where(
            ScoreboardCache.contest_id == contest_id,
            ScoreboardCache.team_id == team_id,
            ScoreboardCache.problem_id == problem_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = ScoreboardCache(
            contest_id=contest_id, team_id=team_id, problem_id=problem_id,
            submissions=0, total_time=0, is_correct=False, score=0.0,
        )
        db.add(entry)
    entry.submissions += 1
    if verdict == Verdict.AC:
        entry.is_correct = True
        entry.score = 100.0
        elapsed = max(0, submit_offset_min)
        entry.total_time = elapsed + (entry.submissions - 1) * 20
    await db.flush()

    return sub


@pytest.mark.asyncio
class TestScoreboard:
    async def test_empty_board(self, async_session):
        db = async_session
        contest, problems = await seed_contest(db)
        await db.commit()

        board = await get_scoreboard(db, contest.id)
        assert board == []

    async def test_one_team_one_ac(self, async_session):
        db = async_session
        contest, problems = await seed_contest(db)
        team = await seed_team(db)
        await db.commit()

        await seed_submission(db, contest.id, problems[0].id, team.id, Verdict.AC, 10)
        await db.commit()

        board = await get_scoreboard(db, contest.id)
        assert len(board) == 1
        assert board[0]["teamname"] == "队伍1"
        assert board[0]["solved"] == 1

    async def test_two_teams_ranking(self, async_session):
        db = async_session
        contest, problems = await seed_contest(db)
        team_a = await seed_team(db, "a", "队伍A")
        team_b = await seed_team(db, "b", "队伍B")
        await db.commit()

        # 队伍A 10分钟 AC，队伍B 5分钟 AC → B 排第一
        await seed_submission(db, contest.id, problems[0].id, team_a.id, Verdict.AC, 10)
        await seed_submission(db, contest.id, problems[0].id, team_b.id, Verdict.AC, 5)
        await db.commit()

        board = await get_scoreboard(db, contest.id)
        assert len(board) == 2
        assert board[0]["teamname"] == "队伍B"  # 更少罚时
        assert board[1]["teamname"] == "队伍A"

    async def test_freeze_hides_results(self, async_session):
        """封榜后，封榜时间之后的提交结果不计入计分板。"""
        db = async_session
        now = datetime.utcnow()

        contest, problems = await seed_contest(db)
        # 设置封榜时间为 30 分钟前
        contest.freeze_time = now - timedelta(minutes=30)
        team = await seed_team(db)
        await db.commit()

        # 封榜前一题 AC（10分前 → 距现在 50分前，在封榜30分之前？不，是50分前 > 30分前，所以是在封榜之前）
        # Let me recalculate: freeze_time = now - 30 min.  Submission at now - 50 min → submit_time < freeze_time, so included
        # 封榜后一题 AC → 应该被排除
        await seed_submission(db, contest.id, problems[0].id, team.id, Verdict.AC, 50)   # 提交于50分钟前，封榜(30分前)之前 → 计入
        await seed_submission(db, contest.id, problems[1].id, team.id, Verdict.AC, 10)   # 提交于10分钟前，封榜之后 → 排除
        await db.commit()

        board = await get_scoreboard(db, contest.id, freeze=True, freeze_time=contest.freeze_time)
        assert len(board) == 1
        assert board[0]["solved"] == 1  # 只计入了封榜前的1题


@pytest.mark.asyncio
class TestIOIScoreboard:
    async def test_ioi_total_score(self, async_session):
        db = async_session
        contest, problems = await seed_contest(db, score_mode="ioi")
        team = await seed_team(db)
        await db.commit()

        # 每题 100 分，IOI 按总分排名
        for p in problems[:2]:
            await seed_submission(db, contest.id, p.id, team.id, Verdict.AC, 5)
        await db.commit()

        board = await get_scoreboard(db, contest.id)
        assert len(board) == 1
        assert board[0]["total_score"] == 200.0
