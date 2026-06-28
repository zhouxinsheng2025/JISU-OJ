from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Auth ──
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    message: str
    redirect: str


# ── User ──
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=64)
    teamname: str


class UserOut(BaseModel):
    id: int
    username: str
    teamname: str
    role: str
    enabled: bool

    class Config:
        from_attributes = True


# ── Contest ──
class ContestCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    score_mode: str = "icpc"
    ctype: str = "contest"
    freeze_time: Optional[datetime] = None


class ContestOut(BaseModel):
    id: int
    title: str
    start_time: datetime
    end_time: datetime
    score_mode: str
    ctype: str
    freeze_time: Optional[datetime] = None
    enabled: bool

    class Config:
        from_attributes = True


# ── Problem (题库) ──
class ProblemCreate(BaseModel):
    pid: str = ""                       # P1001，留空自动生成
    title: str
    description: str = ""
    difficulty: str = "easy"
    tags: str = ""
    time_limit: float = 1.0
    memory_limit: int = 256


class ProblemOut(BaseModel):
    id: int
    pid: str
    title: str
    description: str
    difficulty: str
    tags: str
    time_limit: float
    memory_limit: int
    order: int

    class Config:
        from_attributes = True


# ── TestCase ──
class TestCaseCreate(BaseModel):
    input: str
    output: str
    is_sample: bool = False
    order: int = 0


class TestCaseOut(BaseModel):
    id: int
    problem_id: int
    input: str
    output: str
    is_sample: bool
    order: int

    class Config:
        from_attributes = True


# ── Submission ──
class SubmissionCreate(BaseModel):
    problem_id: int
    language: str
    source_code: str = Field(max_length=256 * 1024)


class SubmissionOut(BaseModel):
    id: int
    contest_id: int
    problem_id: int
    team_id: int
    language: str
    submit_time: datetime
    state: str
    result: Optional[str] = None
    score: Optional[float] = None

    class Config:
        from_attributes = True


# ── Clarification ──
class ClarificationCreate(BaseModel):
    question: str


class ClarificationReply(BaseModel):
    answer: str


class ClarificationOut(BaseModel):
    id: int
    contest_id: int
    sender_teamname: str
    question: str
    answer: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
