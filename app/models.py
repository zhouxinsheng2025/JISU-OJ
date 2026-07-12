from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    JURY = "jury"
    TEAM = "team"


class ScoreMode(str, enum.Enum):
    ICPC = "icpc"
    IOI = "ioi"


class ContestType(str, enum.Enum):
    CONTEST = "contest"      # 正式比赛（限时）
    PRACTICE = "practice"    # 开放练习（不限时）
    HOMEWORK = "homework"    # 作业（限时但灵活）


class SubmissionState(str, enum.Enum):
    QUEUED = "queued"
    JUDGING = "judging"
    DONE = "done"


class Verdict(str, enum.Enum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    RTE = "RTE"
    OLE = "OLE"
    CE = "CE"
    PE = "PE"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    teamname = Column(String(128), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.TEAM)
    enabled = Column(Boolean, default=True, nullable=False)

    submissions = relationship("Submission", back_populates="team")
    clarifications_sent = relationship("Clarification", foreign_keys="Clarification.sender_id", back_populates="sender")
    clarifications_rcvd = relationship("Clarification", foreign_keys="Clarification.recipient_id", back_populates="recipient")
    progress = relationship("UserProgress", back_populates="user")


class Contest(Base):
    __tablename__ = "contests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    score_mode = Column(SAEnum(ScoreMode), nullable=False, default=ScoreMode.ICPC)
    ctype = Column(SAEnum(ContestType), nullable=False, default=ContestType.CONTEST)
    freeze_time = Column(DateTime, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)

    problems = relationship("ContestProblem", back_populates="contest")
    submissions = relationship("Submission", back_populates="contest")
    clarifications = relationship("Clarification", back_populates="contest")


class Problem(Base):
    """题库题目 — 独立于比赛存在"""
    __tablename__ = "problems"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pid = Column(String(32), unique=True, nullable=False, index=True)   # P + 时间戳 + 随机后缀
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    difficulty = Column(SAEnum(Difficulty), default=Difficulty.EASY)
    tags = Column(String(256), default="")          # 逗号分隔: "DP,图论,贪心"
    time_limit = Column(Float, default=1.0)
    memory_limit = Column(Integer, default=256)
    order = Column(Integer, default=0)

    testcases = relationship("TestCase", back_populates="problem")
    submissions = relationship("Submission", back_populates="problem")
    contest_links = relationship("ContestProblem", back_populates="problem")
    progress = relationship("UserProgress", back_populates="problem")


class ContestProblem(Base):
    """比赛与题目的多对多关联（含比赛内排序）"""
    __tablename__ = "contest_problems"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    order = Column(Integer, default=0)  # 比赛内的题目顺序

    contest = relationship("Contest", back_populates="problems")
    problem = relationship("Problem", back_populates="contest_links")

    __table_args__ = (
        UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
    )


class TestCase(Base):
    __tablename__ = "testcases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    input = Column(Text, default="")
    output = Column(Text, default="")
    is_sample = Column(Boolean, default=False)
    order = Column(Integer, default=0)

    problem = relationship("Problem", back_populates="testcases")
    judgeruns = relationship("JudgeRun", back_populates="testcase")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    language = Column(String(16), nullable=False)
    source_code = Column(Text, nullable=False)
    submit_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    state = Column(SAEnum(SubmissionState), default=SubmissionState.QUEUED, nullable=False)

    contest = relationship("Contest", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    team = relationship("User", back_populates="submissions")
    judgings = relationship("Judging", back_populates="submission")


class Judging(Base):
    __tablename__ = "judgings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    result = Column(SAEnum(Verdict), nullable=True)
    score = Column(Float, default=0.0)
    started = Column(DateTime, nullable=True)
    ended = Column(DateTime, nullable=True)

    submission = relationship("Submission", back_populates="judgings")
    judgeruns = relationship("JudgeRun", back_populates="judging")


class JudgeRun(Base):
    __tablename__ = "judgeruns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    judging_id = Column(Integer, ForeignKey("judgings.id"), nullable=False)
    testcase_id = Column(Integer, ForeignKey("testcases.id"), nullable=False)
    result = Column(SAEnum(Verdict), nullable=True)
    runtime = Column(Float, default=0.0)
    output = Column(Text, default="")

    judging = relationship("Judging", back_populates="judgeruns")
    testcase = relationship("TestCase", back_populates="judgeruns")


class Clarification(Base):
    __tablename__ = "clarifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    contest = relationship("Contest", back_populates="clarifications")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="clarifications_sent")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="clarifications_rcvd")


class ScoreboardCache(Base):
    __tablename__ = "scoreboard"
    __table_args__ = (UniqueConstraint("contest_id", "team_id", "problem_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    submissions = Column(Integer, default=0)
    total_time = Column(Integer, default=0)
    is_correct = Column(Boolean, default=False)
    score = Column(Float, default=0.0)


class UserProgress(Base):
    """用户刷题进度追踪"""
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    ac_count = Column(Integer, default=0)           # AC次数
    total_submissions = Column(Integer, default=0)  # 总提交次数
    first_ac_time = Column(DateTime, nullable=True) # 首次AC时间

    user = relationship("User", back_populates="progress")
    problem = relationship("Problem", back_populates="progress")

    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_user_problem_progress"),
    )
