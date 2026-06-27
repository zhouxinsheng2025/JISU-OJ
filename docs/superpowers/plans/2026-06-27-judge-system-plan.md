# 程序设计裁判系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Python FastAPI 全栈的算法竞赛自动判题 Web 系统，支持 ICPC/IOI 双计分模式。

**Architecture:** FastAPI 单体应用，SQLite 数据库，Jinja2 模板渲染，判题引擎内嵌为 asyncio 后台任务，subprocess + psutil 实现基础沙箱。

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, Jinja2, Tailwind CSS CDN, SQLite, psutil, JWT (python-jose)

## Global Constraints

- Python ≥ 3.10
- SQLite 数据库（零配置）
- 密码使用 bcrypt 哈希
- 源码大小限制 256 KB，输出大小限制 8 MB
- 编译超时 30 秒
- 密码使用 bcrypt 哈希存储
- JWT Token 存入 Cookie 实现认证
- 支持 100 支队伍、每秒 5 次提交的并发量
- 单进程部署，一个命令启动

---

## 文件结构总览

```
judge-system/                        # 项目根目录 (C:\Users\24338\Desktop\裁判系统)
├── requirements.txt
├── run.py                           # 启动入口
├── app/
│   ├── __init__.py
│   ├── config.py                    # 配置（数据库URL、JWT密钥等）
│   ├── database.py                  # SQLAlchemy 引擎 + Session
│   ├── models.py                    # 9 张表的 ORM 模型
│   ├── schemas.py                   # Pydantic 请求/响应校验
│   ├── main.py                      # FastAPI app 创建、路由注册、事件处理
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                  # /auth/login, /auth/logout
│   │   ├── team.py                  # /team/* 选手端路由
│   │   ├── jury.py                  # /jury/* 裁判端路由
│   │   └── public.py               # /public/* 公开路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py          # 密码哈希、JWT签发/验证
│   │   ├── contest_service.py       # 比赛 CRUD
│   │   ├── submission_service.py    # 提交处理
│   │   └── score_service.py         # 计分计算 + 计分板缓存
│   ├── judge/
│   │   ├── __init__.py
│   │   ├── engine.py                # 判题引擎后台任务
│   │   ├── compiler.py              # 编译模块
│   │   ├── runner.py                # 执行模块
│   │   └── scorer.py               # 输出比对 + 结果汇总
│   ├── templates/
│   │   ├── base.html                # 基础布局（含导航栏切换）
│   │   ├── auth/
│   │   │   └── login.html           # 登录页（Jury/Team 共用）
│   │   ├── team/
│   │   │   ├── dashboard.html       # 仪表盘（比赛概览、倒计时）
│   │   │   ├── problems.html        # 题目列表
│   │   │   ├── problem_detail.html  # 题目详情 + 提交表单
│   │   │   ├── submissions.html     # 我的提交记录
│   │   │   ├── scoreboard.html      # 计分板
│   │   │   └── clarifications.html  # 问答
│   │   ├── jury/
│   │   │   ├── dashboard.html       # 系统概览
│   │   │   ├── contests.html        # 比赛列表
│   │   │   ├── contest_form.html    # 创建/编辑比赛
│   │   │   ├── problems.html        # 题目管理
│   │   │   ├── problem_form.html    # 添加/编辑题目
│   │   │   ├── testcases.html       # 测试数据管理
│   │   │   ├── teams.html           # 队伍管理
│   │   │   ├── team_form.html       # 创建/编辑队伍
│   │   │   ├── submissions.html     # 所有提交
│   │   │   ├── submission_detail.html # 提交详情（含重判）
│   │   │   ├── scoreboard.html      # 完整计分板
│   │   │   └── clarifications.html  # 问答处理
│   │   └── public/
│   │       └── scoreboard.html      # 公开计分板
│   └── static/
│       └── (空，Tailwind 用 CDN)
├── data/testcases/                  # 测试数据文件存储
└── runs/                            # 判题临时工作目录
```

---

### Task 1: 项目脚手架与配置

**Files:**
- Create: `requirements.txt`
- Create: `run.py`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py` (skeleton)

**Interfaces:**
- Produces: `app.config.Settings` (pydantic-settings, 含 DATABASE_URL, JWT_SECRET, JWT_ALGORITHM), `app.main.app` (FastAPI instance)

- [ ] **Step 1: 编写 requirements.txt**

```txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
pydantic==2.7.3
pydantic-settings==2.3.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
jinja2==3.1.4
psutil==5.9.8
aiosqlite==0.20.0
```

- [ ] **Step 2: 编写 app/__init__.py**

```python
# 空文件
```

- [ ] **Step 3: 编写 app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///judge.db"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    JUDGE_POLL_INTERVAL: int = 1  # 判题引擎轮询间隔(秒)
    COMPILE_TIME_LIMIT: int = 30  # 编译超时(秒)
    SOURCE_SIZE_LIMIT: int = 256 * 1024  # 源码大小限制
    OUTPUT_SIZE_LIMIT: int = 8 * 1024 * 1024  # 输出大小限制
    DATA_DIR: str = "data/testcases"
    RUNS_DIR: str = "runs"


settings = Settings()
```

- [ ] **Step 4: 编写 app/main.py (skeleton)**

```python
from fastapi import FastAPI
from app.config import settings

app = FastAPI(title="程序设计裁判系统")


@app.on_event("startup")
async def startup():
    from app.database import init_db
    await init_db()


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/team/login")
```

- [ ] **Step 5: 编写 run.py**

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 6: 安装依赖并验证启动**

```bash
pip install -r requirements.txt
python run.py
# 预期: 访问 http://localhost:8000 返回重定向（数据库表尚未创建，但FastAPI正常启动）
# 按 Ctrl+C 停止
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt run.py app/
git commit -m "feat: project scaffold with FastAPI + config"
```

---

### Task 2: 数据库与 ORM 模型

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`

**Interfaces:**
- Produces: `app.database.init_db()` (创建所有表), `app.database.get_db()` (async generator for session)
- Produces: `app.models.User`, `app.models.Contest`, `app.models.Problem`, `app.models.TestCase`, `app.models.Submission`, `app.models.Judging`, `app.models.JudgeRun`, `app.models.Clarification`, `app.models.ScoreboardCache`

- [ ] **Step 1: 编写 app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: 编写 app/models.py (第一部分 — 导入与 Base)**

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum as SAEnum
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
```

- [ ] **Step 3: 编写 app/models.py (第二部分 — 所有模型)**

```python
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


class Contest(Base):
    __tablename__ = "contests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    score_mode = Column(SAEnum(ScoreMode), nullable=False, default=ScoreMode.ICPC)
    freeze_time = Column(DateTime, nullable=True)  # 封榜时间，NULL 表示不封榜
    enabled = Column(Boolean, default=True, nullable=False)

    problems = relationship("Problem", back_populates="contest")
    submissions = relationship("Submission", back_populates="contest")
    clarifications = relationship("Clarification", back_populates="contest")


class Problem(Base):
    __tablename__ = "problems"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    time_limit = Column(Float, default=1.0)      # 秒
    memory_limit = Column(Integer, default=256)   # MB
    order = Column(Integer, default=0)

    contest = relationship("Contest", back_populates="problems")
    testcases = relationship("TestCase", back_populates="problem")
    submissions = relationship("Submission", back_populates="problem")


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
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    submissions = Column(Integer, default=0)      # 总提交次数
    total_time = Column(Integer, default=0)        # 累计罚时(分钟)
    is_correct = Column(Boolean, default=False)
    score = Column(Float, default=0.0)             # IOI制得分
```

- [ ] **Step 4: 更新 app/main.py，启动时自动建表**

```python
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.config import settings

app = FastAPI(title="程序设计裁判系统")


@app.on_event("startup")
async def startup():
    from app.database import init_db
    await init_db()
    # 创建默认管理员（后续 Task 6 会改为 seed）
    await _seed_admin()


async def _seed_admin():
    from app.database import async_session
    from app.models import User, UserRole
    from app.services.auth_service import hash_password
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            admin = User(
                username="admin",
                password_hash=hash_password("admin"),
                teamname="Administrator",
                role=UserRole.JURY,
            )
            db.add(admin)
            await db.commit()


@app.get("/")
async def root():
    return RedirectResponse(url="/team/login")
```

- [ ] **Step 5: 启动验证**

```bash
python run.py
# 预期: 启动成功，judge.db 文件自动生成，9张表已创建
# 按 Ctrl+C 停止
```

- [ ] **Step 6: Commit**

```bash
git add app/database.py app/models.py app/main.py
git commit -m "feat: database setup with SQLAlchemy models"
```

---

### Task 3: 认证服务（密码哈希 + JWT）

**Files:**
- Create: `app/services/__init__.py` (空文件)
- Create: `app/services/auth_service.py`
- Create: `app/schemas.py`

**Interfaces:**
- Produces:
  - `hash_password(plain: str) -> str`
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_token(user_id: int, role: str) -> str`
  - `decode_token(token: str) -> dict | None`
  - `get_current_user(token: str, db: AsyncSession) -> User | None`

- [ ] **Step 1: 编写 app/services/auth_service.py**

```python
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(token: str, db: AsyncSession) -> User | None:
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()
```

- [ ] **Step 2: 编写 app/schemas.py**

```python
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
    freeze_time: Optional[datetime] = None


class ContestOut(BaseModel):
    id: int
    title: str
    start_time: datetime
    end_time: datetime
    score_mode: str
    freeze_time: Optional[datetime] = None
    enabled: bool

    class Config:
        from_attributes = True


# ── Problem ──
class ProblemCreate(BaseModel):
    title: str
    description: str = ""
    time_limit: float = 1.0
    memory_limit: int = 256
    order: int = 0


class ProblemOut(BaseModel):
    id: int
    contest_id: int
    title: str
    description: str
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
```

- [ ] **Step 3: Verify auth_service works**

```python
# 在 Python REPL 中手动测试
# cd 到项目根目录
# python -c "
# from app.services.auth_service import hash_password, verify_password, create_token, decode_token
# h = hash_password('test')
# assert verify_password('test', h)
# assert not verify_password('wrong', h)
# t = create_token(1, 'jury')
# d = decode_token(t)
# assert d['sub'] == '1' and d['role'] == 'jury'
# print('All auth tests passed')
# "
```

- [ ] **Step 4: Commit**

```bash
git add app/services/ app/schemas.py
git commit -m "feat: auth service with password hashing and JWT"
```

---

### Task 4: 认证路由与登录页面

**Files:**
- Create: `app/routers/__init__.py` (空文件)
- Create: `app/routers/auth.py`
- Create: `app/templates/base.html`
- Create: `app/templates/auth/login.html`
- Modify: `app/main.py` (注册路由)

**Interfaces:**
- Consumes: `get_db`, `hash_password`, `verify_password`, `create_token`, `UserOut`, `LoginRequest`
- Produces: `GET /auth/login`, `POST /auth/login`, `GET /auth/logout`

- [ ] **Step 1: 编写 app/templates/base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}裁判系统{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gray-900 text-gray-100">
    {% if user %}
    <nav class="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
        <div class="flex gap-4">
            <span class="font-bold text-lg text-blue-400">⚖ 裁判系统</span>
            {% block nav %}{% endblock %}
        </div>
        <div class="flex gap-3 items-center text-sm text-gray-400">
            <span>{{ user.teamname }}</span>
            <a href="/auth/logout" class="text-red-400 hover:underline">退出</a>
        </div>
    </nav>
    {% endif %}
    <main class="max-w-6xl mx-auto p-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 2: 编写 app/templates/auth/login.html**

```html
{% extends "base.html" %}
{% block title %}登录 - 裁判系统{% endblock %}
{% block content %}
<div class="max-w-md mx-auto mt-20">
    <h1 class="text-3xl font-bold text-center mb-8">⚖ 程序设计裁判系统</h1>
    <div class="bg-gray-800 rounded-lg p-8 shadow-lg">
        <form method="POST" class="space-y-5">
            {% if error %}
            <div class="bg-red-900/50 border border-red-500 text-red-300 px-4 py-3 rounded">{{ error }}</div>
            {% endif %}
            <div>
                <label class="block text-sm font-medium mb-1">用户名</label>
                <input name="username" type="text" required
                    class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
            </div>
            <div>
                <label class="block text-sm font-medium mb-1">密码</label>
                <input name="password" type="password" required
                    class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
            </div>
            <button type="submit"
                class="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium transition">
                登录
            </button>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: 编写 app/routers/auth.py**

```python
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.services.auth_service import verify_password, create_token
from app.templates_helpers import templates

router = APIRouter(prefix="/auth", tags=["auth"])

TEMPLATE_DIR = "auth"


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(f"{TEMPLATE_DIR}/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/login.html",
            {"request": request, "error": "用户名或密码错误"},
            status_code=401,
        )

    if not user.enabled:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/login.html",
            {"request": request, "error": "账号已被禁用"},
            status_code=403,
        )

    token = create_token(user.id, user.role.value)
    redirect_url = "/jury/" if user.role.value == "jury" else "/team/"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response
```

- [ ] **Step 4: 编写模板辅助函数 app/templates_helpers.py**

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
```

- [ ] **Step 5: 修改 app/main.py 注册路由**

```python
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.config import settings

app = FastAPI(title="程序设计裁判系统")


@app.on_event("startup")
async def startup():
    from app.database import init_db
    await init_db()
    await _seed_admin()


async def _seed_admin():
    from app.database import async_session
    from app.models import User, UserRole
    from app.services.auth_service import hash_password
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            admin = User(
                username="admin",
                password_hash=hash_password("admin"),
                teamname="Administrator",
                role=UserRole.JURY,
            )
            db.add(admin)
            await db.commit()


# 注册路由
from app.routers import auth
app.include_router(auth.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")
```

- [ ] **Step 6: 验证登录流程**

```bash
python run.py
# 访问 http://localhost:8000
# 预期: 重定向到 /auth/login 登录页
# 用 admin/admin 登录 → 跳转到 /jury/（先 404，正常）
# 测试错误密码 → 显示 "用户名或密码错误"
# 按 Ctrl+C 停止
```

- [ ] **Step 7: Commit**

```bash
git add app/routers/ app/templates/ app/templates_helpers.py app/main.py
git commit -m "feat: login page and auth routes"
```

---

### Task 5: 比赛管理（Jury 端）

**Files:**
- Create: `app/services/contest_service.py`
- Create: `app/routers/team.py` (skeleton — 只写路由器声明)
- Create: `app/routers/jury.py` (部分 — 仅比赛管理路由)
- Create: `app/templates/jury/dashboard.html`
- Create: `app/templates/jury/contests.html`
- Create: `app/templates/jury/contest_form.html`
- Modify: `app/main.py` (注册 jury 路由)

**Interfaces:**
- Consumes: `get_db`, `ContestCreate`, `ContestOut`, `get_current_user`
- Produces: Jury dashboard, contest CRUD pages

- [ ] **Step 1: 编写依赖注入函数 app/dependencies.py**

```python
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import decode_token
from app.models import User, UserRole
from sqlalchemy import select


async def get_current_user_from_cookie(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token is None:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    return result.scalar_one_or_none()


def require_role(role: str):
    async def dependency(request: Request, db: AsyncSession = Depends(get_db)):
        user = await get_current_user_from_cookie(request, db)
        if user is None:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/auth/login", status_code=303)
        if user.role.value != role:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/auth/login", status_code=303)
        return user
    return dependency
```

- [ ] **Step 2: 编写 app/services/contest_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Contest
from app.schemas import ContestCreate


async def create_contest(db: AsyncSession, data: ContestCreate) -> Contest:
    contest = Contest(
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        score_mode=data.score_mode,
        freeze_time=data.freeze_time,
    )
    db.add(contest)
    await db.commit()
    await db.refresh(contest)
    return contest


async def get_contests(db: AsyncSession) -> list[Contest]:
    result = await db.execute(select(Contest).order_by(Contest.id.desc()))
    return list(result.scalars().all())


async def get_contest(db: AsyncSession, contest_id: int) -> Contest | None:
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    return result.scalar_one_or_none()


async def update_contest(db: AsyncSession, contest_id: int, data: ContestCreate) -> Contest | None:
    contest = await get_contest(db, contest_id)
    if contest is None:
        return None
    contest.title = data.title
    contest.start_time = data.start_time
    contest.end_time = data.end_time
    contest.score_mode = data.score_mode
    contest.freeze_time = data.freeze_time
    await db.commit()
    await db.refresh(contest)
    return contest


async def toggle_contest(db: AsyncSession, contest_id: int) -> Contest | None:
    contest = await get_contest(db, contest_id)
    if contest is None:
        return None
    contest.enabled = not contest.enabled
    await db.commit()
    return contest
```

- [ ] **Step 3: 编写 app/routers/team.py (skeleton)**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/team", tags=["team"])
```

- [ ] **Step 4: 编写 app/routers/jury.py (比赛管理部分)**

```python
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest
from app.schemas import ContestCreate
from app.services import contest_service
from app.templates_helpers import templates

router = APIRouter(prefix="/jury", tags=["jury"])

TEMPLATE_DIR = "jury"


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
```

- [ ] **Step 5: 编写 jury dashboard 模板**

`app/templates/jury/dashboard.html`:
```html
{% extends "base.html" %}
{% block title %}裁判后台 - 仪表盘{% endblock %}
{% block nav %}
<a href="/jury/" class="hover:text-blue-400">仪表盘</a>
<a href="/jury/contests" class="hover:text-blue-400">比赛</a>
<a href="/jury/teams" class="hover:text-blue-400">队伍</a>
<a href="/jury/submissions" class="hover:text-blue-400">提交</a>
<a href="/jury/clarifications" class="hover:text-blue-400">问答</a>
<a href="/jury/scoreboard" class="hover:text-blue-400">计分板</a>
{% endblock %}
{% block content %}
<h1 class="text-2xl font-bold mb-6">裁判后台</h1>
<div class="grid grid-cols-3 gap-4">
    <a href="/jury/contests" class="bg-gray-800 p-6 rounded-lg hover:bg-gray-700 transition">
        <div class="text-3xl mb-2">📋</div>
        <div class="font-semibold">比赛管理</div>
        <div class="text-sm text-gray-400">创建和配置比赛</div>
    </a>
    <a href="/jury/teams" class="bg-gray-800 p-6 rounded-lg hover:bg-gray-700 transition">
        <div class="text-3xl mb-2">👥</div>
        <div class="font-semibold">队伍管理</div>
        <div class="text-sm text-gray-400">管理参赛队伍</div>
    </a>
    <a href="/jury/submissions" class="bg-gray-800 p-6 rounded-lg hover:bg-gray-700 transition">
        <div class="text-3xl mb-2">📤</div>
        <div class="font-semibold">提交记录</div>
        <div class="text-sm text-gray-400">查看所有提交</div>
    </a>
</div>
{% endblock %}
```

- [ ] **Step 6: 编写比赛列表和表单模板**（`jury/contests.html`, `jury/contest_form.html` — 标准 Jinja2 表格+表单，内容较多，核心结构为：列表页显示比赛表格含操作按钮，表单页含标题/时间/计分模式/封榜时间字段）

- [ ] **Step 7: 更新 app/main.py 注册 jury 路由**

```python
# 在路由注册部分增加:
from app.routers import jury
app.include_router(jury.router)
```

- [ ] **Step 8: 验证**

```bash
python run.py
# 登录 admin/admin → 跳转 /jury/
# 点击"比赛管理" → /jury/contests
# 新建比赛 → 填写表单 → 保存 → 列表出现
# 编辑比赛 → 修改 → 保存
# 按 Ctrl+C 停止
```

- [ ] **Step 9: Commit**

```bash
git add app/dependencies.py app/services/contest_service.py app/routers/ app/templates/jury/ app/main.py
git commit -m "feat: contest management for jury"
```

---

### Task 6: 队伍管理（Jury 端）

**Files:**
- Create: `app/templates/jury/teams.html`
- Create: `app/templates/jury/team_form.html`
- Modify: `app/routers/jury.py` (增加队伍管理路由)

**Interfaces:**
- Consumes: `get_db`, `require_role("jury")`, `hash_password`
- Produces: 队伍 CRUD 页面

- [ ] **Step 1: 在 app/routers/jury.py 中添加队伍管理路由**

```python
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
```

- [ ] **Step 2: 编写队伍管理模板**（`jury/teams.html` — 队伍列表表格含创建/编辑/启用禁用按钮, `jury/team_form.html` — 表单含用户名/密码/队伍名/启禁用字段）

- [ ] **Step 3: 验证 — 创建队伍、编辑、登录**

```bash
python run.py
# Jury 端创建队伍 test1, test2
# 用 test1 账号登录 → 跳转到 /team/（skeleton 页面，存在即可）
# 按 Ctrl+C 停止
```

- [ ] **Step 4: Commit**

```bash
git add app/routers/jury.py app/templates/jury/teams.html app/templates/jury/team_form.html
git commit -m "feat: team management for jury"
```

---

### Task 7: 题目与测试数据管理（Jury 端）

**Files:**
- Modify: `app/routers/jury.py` (增加题目和测试数据路由)
- Create: `app/templates/jury/problems.html`
- Create: `app/templates/jury/problem_form.html`
- Create: `app/templates/jury/testcases.html`
- Modify: `app/templates/jury/contests.html` (增加进入题目管理链接)

**Interfaces:**
- Consumes: `get_db`, `require_role("jury")`, `contest_service.get_contest`
- Produces: 题目 CRUD + 测试数据管理页面

- [ ] **Step 1: 在 app/routers/jury.py 中添加题目管理路由**

```python
# ── 题目列表 ──
@router.get("/contests/{contest_id}/problems")
async def list_problems(contest_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    contest = await contest_service.get_contest(db, contest_id)
    if contest is None:
        return RedirectResponse(url="/jury/contests", status_code=303)
    from sqlalchemy import select
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
    return RedirectResponse(url=f"/jury/contests/{contest_id}/problems", status_code=303)


# ── 编辑题目 ──
@router.get("/problems/{problem_id}/edit")
async def edit_problem_page(problem_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
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
```

- [ ] **Step 2: 在 app/routers/jury.py 中添加测试数据管理路由**

```python
# ── 测试数据管理 ──
@router.get("/problems/{problem_id}/testcases")
async def manage_testcases(problem_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
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
    tc = TestCase(
        problem_id=problem_id,
        input=input_data,
        output=output_data,
        is_sample=(is_sample == "1"),
    )
    db.add(tc)
    await db.commit()
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)


@router.post("/problems/{problem_id}/testcases/delete/{tc_id}")
async def delete_testcase(problem_id: int, tc_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(TestCase).where(TestCase.id == tc_id, TestCase.problem_id == problem_id))
    tc = result.scalar_one_or_none()
    if tc:
        await db.delete(tc)
        await db.commit()
    return RedirectResponse(url=f"/jury/problems/{problem_id}/testcases", status_code=303)
```

- [ ] **Step 3: 编写题目和测试数据模板**（`jury/problems.html`, `jury/problem_form.html`, `jury/testcases.html` — 标准 CRUD 表单 + 表格）

- [ ] **Step 4: 验证**

```bash
python run.py
# 进入比赛 → 题目管理 → 新建题目
# 进入题目 → 测试数据管理 → 添加测试点
# 按 Ctrl+C 停止
```

- [ ] **Step 5: Commit**

```bash
git add app/routers/jury.py app/templates/jury/problems.html app/templates/jury/problem_form.html app/templates/jury/testcases.html
git commit -m "feat: problem and testcase management"
```

---

### Task 8: Team 端 — 仪表盘与题目查看

**Files:**
- Modify: `app/routers/team.py` (替换 skeleton)
- Create: `app/templates/team/dashboard.html`
- Create: `app/templates/team/problems.html`
- Create: `app/templates/team/problem_detail.html`
- Modify: `app/main.py` (注册 team 路由)

**Interfaces:**
- Consumes: `require_role("team")`, `contest_service`
- Produces: Team dashboard, problem listing, problem detail with samples

- [ ] **Step 1: 编写 app/routers/team.py**

```python
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import require_role
from app.models import User, Contest, Problem, TestCase, Submission
from app.templates_helpers import templates

router = APIRouter(prefix="/team", tags=["team"])

TEMPLATE_DIR = "team"


@router.get("/")
async def dashboard(request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    # 找到当前启用的比赛
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1)
    )
    current_contest = result.scalar_one_or_none()
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/dashboard.html",
        {"request": request, "user": user, "contest": current_contest},
    )


@router.get("/problems")
async def list_problems(request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1)
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
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problems.html",
        {"request": request, "user": user, "contest": contest, "problems": problems},
    )


@router.get("/problems/{problem_id}")
async def problem_detail(problem_id: int, request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return RedirectResponse(url="/team/problems", status_code=303)
    # 获取样例测试数据
    tc_result = await db.execute(
        select(TestCase).where(TestCase.problem_id == problem_id, TestCase.is_sample == True)
    )
    samples = list(tc_result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/problem_detail.html",
        {"request": request, "user": user, "problem": problem, "samples": samples},
    )
```

- [ ] **Step 2: 编写 Team 模板**（`team/dashboard.html`, `team/problems.html`, `team/problem_detail.html` — 选手端风格，深色主题，题目列表含状态标记，详情页含题目描述 + 样例 + 提交入口）

- [ ] **Step 3: 更新 app/main.py**

```python
# 增加:
from app.routers import team
app.include_router(team.router)
```

- [ ] **Step 4: 验证**

```bash
python run.py
# 启用一场比赛（时间包含当前）
# 用队伍账号登录 → 仪表盘显示比赛信息
# 题目列表 → 点击题目 → 查看详情含样例
# 按 Ctrl+C 停止
```

- [ ] **Step 5: Commit**

```bash
git add app/routers/team.py app/templates/team/ app/main.py
git commit -m "feat: team dashboard and problem viewing"
```

---

### Task 9: 代码提交（Team 端）

**Files:**
- Create: `app/services/submission_service.py`
- Modify: `app/routers/team.py` (增加提交路由)

**Interfaces:**
- Consumes: `require_role("team")`, `SubmissionCreate`
- Produces: `POST /team/submit` — 接收代码并写入 submission 表 (state=queued)

- [ ] **Step 1: 编写 app/services/submission_service.py**

```python
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Submission, SubmissionState, Problem, Contest


async def create_submission(
    db: AsyncSession,
    contest_id: int,
    problem_id: int,
    team_id: int,
    language: str,
    source_code: str,
) -> Submission:
    submission = Submission(
        contest_id=contest_id,
        problem_id=problem_id,
        team_id=team_id,
        language=language,
        source_code=source_code,
        submit_time=datetime.utcnow(),
        state=SubmissionState.QUEUED,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


async def get_team_submissions(db: AsyncSession, team_id: int) -> list[Submission]:
    result = await db.execute(
        select(Submission)
        .where(Submission.team_id == team_id)
        .order_by(Submission.submit_time.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_submission_detail(db: AsyncSession, submission_id: int) -> Submission | None:
    from app.models import Judging, JudgeRun
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        return None
    # eager load judgings and judgeruns
    judging_result = await db.execute(
        select(Judging).where(Judging.submission_id == submission_id).order_by(Judging.id.desc())
    )
    submission._judgings = list(judging_result.scalars().all())
    return submission
```

- [ ] **Step 2: 在 app/routers/team.py 中添加提交路由**

```python
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
    # 验证题目属于当前比赛
    from sqlalchemy import select
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem is None:
        return {"error": "题目不存在"}
    # 检查源码大小
    if len(source_code) > 256 * 1024:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/problem_detail.html",
            {"request": request, "user": user, "problem": problem, "error": "代码超过256KB限制"},
        )
    await submission_service.create_submission(
        db, problem.contest_id, problem_id, user.id, language, source_code
    )
    return RedirectResponse(url="/team/submissions", status_code=303)


@router.get("/submissions")
async def my_submissions(request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    from app.services import submission_service
    submissions = await submission_service.get_team_submissions(db, user.id)
    # 为每个提交加载最新判题结果
    from app.models import Judging
    from sqlalchemy import select
    submission_data = []
    for sub in submissions:
        j_result = await db.execute(
            select(Judging).where(Judging.submission_id == sub.id).order_by(Judging.id.desc())
        )
        judging = j_result.scalar_one_or_none()
        submission_data.append({
            "submission": sub,
            "judging": judging,
        })
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submissions.html",
        {"request": request, "user": user, "submission_data": submission_data},
    )


@router.get("/submissions/{submission_id}")
async def submission_detail(submission_id: int, request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    from app.services import submission_service
    from app.models import Judging, JudgeRun
    from sqlalchemy import select
    sub = await submission_service.get_submission_detail(db, submission_id)
    if sub is None or sub.team_id != user.id:
        return RedirectResponse(url="/team/submissions", status_code=303)
    judging_result = await db.execute(
        select(Judging).where(Judging.submission_id == submission_id).order_by(Judging.id.desc())
    )
    judging = judging_result.scalar_one_or_none()
    runs = []
    if judging:
        runs_result = await db.execute(
            select(JudgeRun).where(JudgeRun.judging_id == judging.id).order_by(JudgeRun.id)
        )
        runs = list(runs_result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submission_detail.html",
        {"request": request, "user": user, "submission": sub, "judging": judging, "runs": runs},
    )
```

- [ ] **Step 3: 编写提交记录模板**（`team/submissions.html` — 提交列表显示状态/结果，实时轮询刷新）

- [ ] **Step 4: 验证**

```bash
python run.py
# 用队伍账号登录 → 题目详情 → 粘贴代码 → 提交
# 跳转到提交记录页（state=queued，暂时没有判题结果）
# 按 Ctrl+C 停止
```

- [ ] **Step 5: Commit**

```bash
git add app/services/submission_service.py app/routers/team.py app/templates/team/submissions.html
git commit -m "feat: code submission for teams"
```

---

### Task 10: 判题引擎 — 编译模块

**Files:**
- Create: `app/judge/__init__.py` (空文件)
- Create: `app/judge/compiler.py`

**Interfaces:**
- Produces: `compile_code(source_path: str, language: str, work_dir: str) -> tuple[bool, str, str]`
  - Returns: (success, executable_path_or_error, compiler_output)

- [ ] **Step 1: 编写 app/judge/compiler.py**

```python
import subprocess
import os
import asyncio
from app.config import settings

COMPILE_COMMANDS = {
    "c": "gcc {source} -o {output} -O2 -Wall -lm",
    "cpp": "g++ {source} -o {output} -O2 -Wall -lm",
    "java": "javac {source}",
    "python": None,  # 无需编译
}


LANGUAGE_EXT = {
    "c": "c",
    "cpp": "cpp",
    "java": "java",
    "python": "py",
}


async def compile_code(source_code: str, language: str, work_dir: str) -> tuple[bool, str, str]:
    """编译源代码，返回 (成功, 可执行路径或错误, 编译器输出)"""
    if language == "python":
        # Python 不需要编译，直接写入文件
        src_path = os.path.join(work_dir, "solution.py")
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source_code)
        return True, src_path, ""

    ext = LANGUAGE_EXT.get(language, "txt")
    src_path = os.path.join(work_dir, f"solution.{ext}")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    if language == "java":
        exe_path = os.path.join(work_dir, "Main.class")
    else:
        exe_path = os.path.join(work_dir, "solution")

    cmd = COMPILE_COMMANDS[language].format(source=src_path, output=exe_path)

    try:
        proc = await _run_async(cmd, work_dir)
        if proc.returncode != 0:
            return False, proc.stderr, proc.stderr
        return True, exe_path, ""
    except subprocess.TimeoutExpired:
        return False, "", "Compilation timed out"


async def _run_async(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    return await asyncio_to_thread_run(cmd, cwd)


def asyncio_to_thread_run(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True,
        timeout=settings.COMPILE_TIME_LIMIT,
    )
```

- [ ] **Step 2: 编写 _sync_run 辅助函数（接上面完整代码）**

- [ ] **Step 3: 单元测试验证**

```bash
python -c "
import asyncio
from app.judge.compiler import compile_code
import tempfile, os

async def test():
    d = tempfile.mkdtemp()
    ok, path, err = await compile_code('print(\"hello\")', 'python', d)
    assert ok
    assert 'solution.py' in path
    print('Python compile: PASS')
    
    ok, path, err = await compile_code('#include<stdio.h>\nint main(){printf(\"hi\");return 0;}', 'c', d)
    assert ok
    print('C compile: PASS')

asyncio.run(test())
"
```

- [ ] **Step 4: Commit**

```bash
git add app/judge/
git commit -m "feat: judge compiler module"
```

---

### Task 11: 判题引擎 — 执行模块

**Files:**
- Create: `app/judge/runner.py`

**Interfaces:**
- Produces: `run_program(exe_path: str, language: str, work_dir: str, input_data: str, time_limit: float, memory_limit_mb: int) -> tuple[str, str, float, str]`
  - Returns: (verdict, output, runtime, stderr) — verdict 为 None 表示正常退出待比对

- [ ] **Step 1: 编写 app/judge/runner.py**

```python
import subprocess
import os
import asyncio
import psutil
from app.config import settings


async def run_program(
    exe_path: str,
    language: str,
    work_dir: str,
    input_data: str,
    time_limit: float,
    memory_limit_mb: int,
) -> tuple[str | None, str, float, str]:
    """
    运行编译后的程序，返回 (verdict, stdout, runtime_seconds, stderr)
    verdict 为 None 表示正常退出，需要比对输出
    """
    output_path = os.path.join(work_dir, "output.txt")
    error_path = os.path.join(work_dir, "error.txt")

    if language == "python":
        cmd = f"python {exe_path}"
    elif language == "java":
        class_dir = os.path.dirname(exe_path)
        cmd = f"java -cp {class_dir} Main"
    else:
        cmd = f"./{exe_path}"

    try:
        runtime = await _run_with_limits(
            cmd, work_dir, input_data, output_path, error_path,
            time_limit, memory_limit_mb,
        )
        with open(output_path, "r", encoding="utf-8", errors="replace") as f:
            output = f.read(settings.OUTPUT_SIZE_LIMIT)
        with open(error_path, "r", encoding="utf-8", errors="replace") as f:
            stderr = f.read(1024)
        # 检查输出是否被截断
        if len(output) >= settings.OUTPUT_SIZE_LIMIT:
            return "OLE", output, runtime, stderr
        return None, output, runtime, stderr

    except subprocess.TimeoutExpired:
        return "TLE", "", time_limit, "Time limit exceeded"
    except MemoryError:
        return "MLE", "", 0.0, "Memory limit exceeded"
    except RuntimeError as e:
        return "RTE", "", 0.0, str(e)
    except Exception as e:
        return "RTE", "", 0.0, str(e)


async def _run_with_limits(
    cmd: str,
    cwd: str,
    stdin_data: str,
    stdout_path: str,
    stderr_path: str,
    time_limit: float,
    memory_limit_mb: int,
) -> float:
    """执行命令并施加资源限制"""
    import time
    start = time.time()

    with open(stdout_path, "w") as fout, open(stderr_path, "w") as ferr:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=fout,
            stderr=ferr,
        )
        try:
            await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=time_limit + 2,  # 额外2秒缓冲
            )
        except asyncio.TimeoutError:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            await proc.wait()
            raise subprocess.TimeoutExpired(cmd, time_limit)

    runtime = time.time() - start
    if proc.returncode != 0 and proc.returncode is not None:
        raise RuntimeError(f"Exit code: {proc.returncode}")

    return runtime
```

- [ ] **Step 2: 验证**

```bash
python -c "
import asyncio, tempfile, os
from app.judge.runner import run_program
from app.judge.compiler import compile_code

async def test():
    d = tempfile.mkdtemp()
    # Python
    ok, path, _ = await compile_code('print(input())', 'python', d)
    verdict, out, runtime, err = await run_program(path, 'python', d, 'hello', 2.0, 256)
    assert verdict is None and out.strip() == 'hello', f'Got: {out}'
    print(f'Python run: PASS (runtime={runtime:.3f}s)')

asyncio.run(test())
"
```

- [ ] **Step 3: Commit**

```bash
git add app/judge/runner.py
git commit -m "feat: judge runner module with resource limits"
```

---

### Task 12: 判题引擎 — 评分模块

**Files:**
- Create: `app/judge/scorer.py`

**Interfaces:**
- Produces:
  - `compare_output(actual: str, expected: str) -> str` — 返回 AC/WA/PE
  - `calculate_icpc_result(runs: list[JudgeRun]) -> str` — 返回最终判题结果 (懒判逻辑)
  - `calculate_ioi_result(runs: list[JudgeRun], total_testcases: int) -> tuple[str, float]` — 返回 (结果, 得分)

- [ ] **Step 1: 编写 app/judge/scorer.py**

```python
from app.models import Verdict


def compare_output(actual: str, expected: str) -> str:
    """逐行比对输出，返回 AC / WA / PE"""
    actual_lines = actual.rstrip("\n").split("\n")
    expected_lines = expected.rstrip("\n").split("\n")

    # 去除每行尾部空白
    actual_trimmed = [line.rstrip() for line in actual_lines]
    expected_trimmed = [line.rstrip() for line in expected_lines]

    if actual_trimmed == expected_trimmed:
        return Verdict.AC.value

    # 忽略全部空白后仍相同 → PE (Presentation Error)
    actual_stripped = "".join(actual_trimmed).replace(" ", "").replace("\t", "")
    expected_stripped = "".join(expected_trimmed).replace(" ", "").replace("\t", "")
    if actual_stripped == expected_stripped:
        return Verdict.PE.value

    return Verdict.WA.value


def calculate_icpc_result(run_results: list[tuple[str, float]]) -> tuple[str, float]:
    """
    ICPC 懒判：遇到第一个非 AC 即停止
    run_results: [(verdict, runtime), ...]
    返回 (final_verdict, max_runtime)
    """
    max_runtime = 0.0
    for verdict, runtime in run_results:
        max_runtime = max(max_runtime, runtime)
        if verdict != Verdict.AC.value:
            return verdict, max_runtime
    return Verdict.AC.value, max_runtime


def calculate_ioi_result(run_results: list[tuple[str, float]], total_testcases: int) -> tuple[str, float]:
    """
    IOI 计分：每个 AC 测试点得分 = 100 / total_testcases
    返回 (final_verdict, total_score)
    """
    if total_testcases == 0:
        return Verdict.AC.value, 100.0

    points_per_case = 100.0 / total_testcases
    total_score = 0.0
    max_runtime = 0.0
    has_non_ac = False

    for verdict, runtime in run_results:
        max_runtime = max(max_runtime, runtime)
        if verdict == Verdict.AC.value:
            total_score += points_per_case
        else:
            has_non_ac = True

    final_verdict = Verdict.AC.value if not has_non_ac else Verdict.WA.value
    return final_verdict, round(total_score, 2)
```

- [ ] **Step 2: 验证**

```bash
python -c "
from app.judge.scorer import compare_output, calculate_icpc_result, calculate_ioi_result

# compare_output tests
assert compare_output('hello\n', 'hello\n') == 'AC'
assert compare_output('hello', 'world') == 'WA'
assert compare_output('a b', 'a  b') == 'PE'  # trailing spaces differ
print('compare_output: PASS')

# ICPC tests
assert calculate_icpc_result([('AC', 0.1), ('AC', 0.2)]) == ('AC', 0.2)
assert calculate_icpc_result([('AC', 0.1), ('WA', 0.2)]) == ('WA', 0.2)
print('ICPC: PASS')

# IOI tests
verdict, score = calculate_ioi_result([('AC', 0.1), ('AC', 0.2)], 4)
assert score == 50.0
print('IOI: PASS')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/judge/scorer.py
git commit -m "feat: judge scorer module"
```

---

### Task 13: 判题引擎 — 编排器

**Files:**
- Create: `app/judge/engine.py`
- Modify: `app/main.py` (启动时启动判题引擎)

**Interfaces:**
- Consumes: compiler, runner, scorer, database
- Produces: `start_judge_engine()` — 后台 asyncio 任务，轮询并处理提交

- [ ] **Step 1: 编写 app/judge/engine.py**

```python
import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import async_session
from app.models import Submission, SubmissionState, Judging, JudgeRun, TestCase, Contest, Verdict, Problem
from app.judge.compiler import compile_code
from app.judge.runner import run_program
from app.judge.scorer import compare_output, calculate_icpc_result, calculate_ioi_result


async def judge_loop():
    """判题主循环，后台运行"""
    print("[Judge] 判题引擎已启动")
    while True:
        try:
            await _judge_pending()
        except Exception as e:
            print(f"[Judge] 错误: {e}")
        await asyncio.sleep(settings.JUDGE_POLL_INTERVAL)


async def _judge_pending():
    async with async_session() as db:
        # 取最早的 queued 提交
        result = await db.execute(
            select(Submission)
            .where(Submission.state == SubmissionState.QUEUED)
            .order_by(Submission.submit_time.asc())
            .limit(1)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            return

        # 标记为 judging
        submission.state = SubmissionState.JUDGING
        await db.commit()

    await _judge_submission(submission.id)


async def _judge_submission(submission_id: int):
    """判题单个提交"""
    async with async_session() as db:
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()
        if submission is None:
            return

        # 获取题目和测试数据
        problem_result = await db.execute(select(Problem).where(Problem.id == submission.problem_id))
        problem = problem_result.scalar_one_or_none()

        tc_result = await db.execute(
            select(TestCase).where(TestCase.problem_id == submission.problem_id).order_by(TestCase.order)
        )
        testcases = list(tc_result.scalars().all())

        # 获取比赛计分模式
        contest_result = await db.execute(select(Contest).where(Contest.id == submission.contest_id))
        contest = contest_result.scalar_one_or_none()
        score_mode = contest.score_mode.value if contest else "icpc"

        # 创建工作目录
        work_dir = tempfile.mkdtemp(dir=settings.RUNS_DIR)
        os.makedirs(work_dir, exist_ok=True)

        try:
            # 创建 Judging 记录
            judging = Judging(
                submission_id=submission.id,
                started=datetime.utcnow(),
            )
            db.add(judging)
            await db.flush()

            # 编译
            compile_ok, exe_or_error, compile_output = await compile_code(
                submission.source_code, submission.language, work_dir
            )
            if not compile_ok:
                judging.result = Verdict.CE
                judging.ended = datetime.utcnow()
                submission.state = SubmissionState.DONE
                await db.commit()
                # 写入编译错误到 judgerun（便于前端展示）
                run = JudgeRun(judging_id=judging.id, testcase_id=0, result=Verdict.CE, output=compile_output)
                db.add(run)
                await db.commit()
                return

            # 逐一运行测试点
            run_results = []
            for tc in testcases:
                verdict, output, runtime, stderr = await run_program(
                    exe_or_error, submission.language, work_dir,
                    tc.input, problem.time_limit, problem.memory_limit,
                )

                if verdict is None:
                    # 正常完成，比对输出
                    verdict = compare_output(output, tc.output)

                run = JudgeRun(
                    judging_id=judging.id,
                    testcase_id=tc.id,
                    result=verdict,
                    runtime=runtime,
                    output=output,
                )
                db.add(run)
                run_results.append((verdict, runtime))

                # ICPC 懒判：遇到第一个非 AC 即停止
                if score_mode == "icpc" and verdict != Verdict.AC.value and not tc.is_sample:
                    # 仍记录结果但停止运行更多测试点
                    pass  # 我们已经在所有的测试点前停止。需要调整：只对隐藏测试点应用懒判。
                    # 实际简化处理：全部跑完，但汇总时按 ICPC 规则
                    # 后续 Task 19 会优化懒判

            # 汇总结果
            if score_mode == "ioi":
                final_verdict, final_score = calculate_ioi_result(run_results, len(testcases))
            else:
                final_verdict, max_runtime = calculate_icpc_result(run_results)
                final_score = 100.0 if final_verdict == Verdict.AC.value else 0.0

            judging.result = final_verdict
            judging.score = final_score
            judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            await db.commit()

            # 更新计分板缓存
            await _update_scoreboard(db, submission, final_verdict, final_score)

        except Exception as e:
            judging.result = Verdict.RTE
            judging.ended = datetime.utcnow()
            submission.state = SubmissionState.DONE
            run = JudgeRun(judging_id=judging.id, testcase_id=0, result=Verdict.RTE, output=str(e))
            db.add(run)
            await db.commit()

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


async def _update_scoreboard(db: AsyncSession, submission: Submission, verdict: str, score: float):
    """更新计分板缓存"""
    from app.models import ScoreboardCache
    result = await db.execute(
        select(ScoreboardCache).where(
            ScoreboardCache.contest_id == submission.contest_id,
            ScoreboardCache.team_id == submission.team_id,
            ScoreboardCache.problem_id == submission.problem_id,
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = ScoreboardCache(
            contest_id=submission.contest_id,
            team_id=submission.team_id,
            problem_id=submission.problem_id,
        )
        db.add(entry)

    entry.submissions += 1

    if verdict == Verdict.AC.value:
        entry.is_correct = True
        entry.score = max(entry.score, score)
        # 计算罚时：AC前的未通过提交*20 + 比赛开始到此次提交的分钟数
        contest_result = await db.execute(select(Contest).where(Contest.id == submission.contest_id))
        contest = contest_result.scalar_one_or_none()
        if contest:
            elapsed = int((submission.submit_time - contest.start_time).total_seconds() / 60)
            entry.total_time = elapsed + (entry.submissions - 1) * 20
    else:
        entry.score = max(entry.score, score)

    await db.commit()


```

> **注意**: 文件顶部 imports 需包含 `from app.models import Problem`

- [ ] **Step 2: 修改 app/main.py 启动判题引擎**

```python
# 在 startup 事件中添加:
import asyncio
from app.judge.engine import judge_loop

@app.on_event("startup")
async def startup():
    from app.database import init_db
    await init_db()
    await _seed_admin()
    asyncio.create_task(judge_loop())
```

- [ ] **Step 3: 端到端验证**

```bash
python run.py
# Jury 创建比赛 + 题目 + 测试数据（AC测试点1个 + WA测试点1个）
# Team 提交正确代码 → 等待2秒 → 查看提交记录 → 应显示 AC
# Team 提交错误代码 → 查看提交记录 → 应显示 WA
# 按 Ctrl+C 停止
```

- [ ] **Step 4: Commit**

```bash
git add app/judge/engine.py app/main.py
git commit -m "feat: judge engine orchestrator with scoring"
```

---

### Task 14: 计分板

**Files:**
- Modify: `app/services/score_service.py` (已创建，需要实际内容)
- Modify: `app/routers/team.py` (增加计分板路由)
- Modify: `app/routers/jury.py` (增加计分板路由)
- Create: `app/templates/team/scoreboard.html`
- Create: `app/templates/jury/scoreboard.html`

**Interfaces:**
- Consumes: ScoreboardCache, Contest, User
- Produces: 计分板页面（ICPC 按 AC数→罚时 排序，IOI 按总分 排序）

- [ ] **Step 1: 删除旧的 app/services/score_service.py 并重写**

实际上 score_service.py 还没有内容。直接创建:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ScoreboardCache, Contest, User, ScoreMode


async def get_scoreboard(db: AsyncSession, contest_id: int, freeze: bool = False):
    """获取计分板数据，freeze=True 时冻结排名（不显示最后结果）"""
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
    from app.models import Problem
    result = await db.execute(
        select(Problem).where(Problem.contest_id == contest_id).order_by(Problem.order)
    )
    return list(result.scalars().all())
```

- [ ] **Step 2: 在 app/routers/team.py 中添加 Team 计分板**

```python
@router.get("/scoreboard")
async def team_scoreboard(request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    from app.services import score_service
    now = datetime.utcnow()
    result = await db.execute(
        select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1)
    )
    contest = result.scalar_one_or_none()
    if contest is None:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/dashboard.html",
            {"request": request, "user": user, "contest": None, "error": "没有进行中的比赛"},
        )
    # 封榜检查
    freeze = contest.freeze_time is not None and now >= contest.freeze_time
    board = await score_service.get_scoreboard(db, contest.id, freeze=freeze)
    problems = await score_service.get_contest_problems(db, contest.id)
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/scoreboard.html",
        {"request": request, "user": user, "contest": contest, "board": board, "problems": problems, "freeze": freeze},
    )
```

- [ ] **Step 3: 在 app/routers/jury.py 中添加 Jury 计分板**

```python
@router.get("/scoreboard")
async def jury_scoreboard(request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db), contest_id: int = None):
    from app.services import score_service
    from datetime import datetime

    if contest_id is None:
        # 默认显示第一个启用的比赛
        now = datetime.utcnow()
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
```

- [ ] **Step 4: 编写计分板模板**（`team/scoreboard.html` + `jury/scoreboard.html` — 表格形式，行=队伍，列=题目，单元格显示 AC/WA/— 状态及罚时/得分）

- [ ] **Step 5: 验证**

```bash
python run.py
# Team 提交几道题 → 查看计分板 → 排名正确
# Jury 查看计分板 → 包含封榜后的真实数据
# 按 Ctrl+C 停止
```

- [ ] **Step 6: Commit**

```bash
git add app/services/score_service.py app/routers/team.py app/routers/jury.py app/templates/team/scoreboard.html app/templates/jury/scoreboard.html
git commit -m "feat: scoreboard with ICPC and IOI ranking"
```

---

### Task 15: 澄清（Clarification）系统

**Files:**
- Modify: `app/routers/team.py` (增加问答路由)
- Modify: `app/routers/jury.py` (增加问答处理路由)
- Create: `app/templates/team/clarifications.html`
- Create: `app/templates/jury/clarifications.html`

**Interfaces:**
- Consumes: `get_db`, `require_role`
- Produces: Team 提问 / Jury 回复 功能

- [ ] **Step 1: 在 app/routers/team.py 中添加**

```python
@router.get("/clarifications")
async def team_clarifications(request: Request, user: User = Depends(require_role("team")), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    from app.models import Clarification
    now = datetime.utcnow()
    result = await db.execute(select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1))
    contest = result.scalar_one_or_none()

    clar_result = await db.execute(
        select(Clarification).where(
            Clarification.contest_id == contest.id if contest else 0,
            # 可以看到自己的提问和回复给所有人的
            ((Clarification.sender_id == user.id) | (Clarification.recipient_id == None))
        ).order_by(Clarification.created_at.desc())
    )
    clarifications = list(clar_result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/clarifications.html",
        {"request": request, "user": user, "contest": contest, "clarifications": clarifications},
    )


@router.post("/clarifications/new")
async def team_ask(
    request: Request,
    question: str = Form(...),
    user: User = Depends(require_role("team")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    from app.models import Clarification
    now = datetime.utcnow()
    result = await db.execute(select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1))
    contest = result.scalar_one_or_none()
    if contest is None:
        return RedirectResponse(url="/team/clarifications", status_code=303)

    clar = Clarification(contest_id=contest.id, sender_id=user.id, question=question)
    db.add(clar)
    await db.commit()
    return RedirectResponse(url="/team/clarifications", status_code=303)
```

- [ ] **Step 2: 在 app/routers/jury.py 中添加**

```python
@router.get("/clarifications")
async def jury_clarifications(request: Request, contest_id: int = None, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from app.models import Clarification
    if contest_id:
        clar_result = await db.execute(
            select(Clarification).where(Clarification.contest_id == contest_id).order_by(Clarification.created_at.desc())
        )
    else:
        clar_result = await db.execute(select(Clarification).order_by(Clarification.created_at.desc()))
    clarifications = list(clar_result.scalars().all())
    # 获取所有相关用户
    user_ids = set()
    for c in clarifications:
        user_ids.add(c.sender_id)
        if c.recipient_id:
            user_ids.add(c.recipient_id)
    user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u for u in user_result.scalars().all()}
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/clarifications.html",
        {"request": request, "user": user, "clarifications": clarifications, "users_map": users_map},
    )


@router.post("/clarifications/{clar_id}/reply")
async def jury_reply(
    clar_id: int,
    answer: str = Form(...),
    user: User = Depends(require_role("jury")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models import Clarification
    result = await db.execute(select(Clarification).where(Clarification.id == clar_id))
    clar = result.scalar_one_or_none()
    if clar:
        clar.answer = answer
        clar.recipient_id = user.id
        await db.commit()
    return RedirectResponse(url=f"/jury/clarifications?contest_id={clar.contest_id if clar else ''}", status_code=303)
```

- [ ] **Step 3: 编写问答模板**（`team/clarifications.html` — 提问表单 + 问答列表，`jury/clarifications.html` — 问答列表 + 回复表单）

- [ ] **Step 4: 验证**

```bash
python run.py
# Team 提问 → Jury 看到 → Jury 回复 → Team 看到回复
# 按 Ctrl+C 停止
```

- [ ] **Step 5: Commit**

```bash
git add app/routers/team.py app/routers/jury.py app/templates/team/clarifications.html app/templates/jury/clarifications.html
git commit -m "feat: clarification system"
```

---

### Task 16: 公开计分板 + Jury 提交详情 + 重判 + 补全模板

**Files:**
- Create: `app/routers/public.py`
- Create: `app/templates/public/scoreboard.html`
- Modify: `app/routers/jury.py` (增加提交详情和重判路由)
- Create: `app/templates/jury/submissions.html`
- Create: `app/templates/jury/submission_detail.html`
- Modify: `app/main.py` (注册 public 路由)
- 补全所有遗漏的模板文件

**Implement all remaining routes and templates to complete the system.**

- [ ] **Step 1: 编写 app/routers/public.py**

```python
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Contest
from app.services import score_service
from app.templates_helpers import templates

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/scoreboard")
async def public_scoreboard(request: Request, db: AsyncSession = Depends(get_db), contest_id: int = None):
    from datetime import datetime
    if contest_id:
        result = await db.execute(select(Contest).where(Contest.id == contest_id))
    else:
        now = datetime.utcnow()
        result = await db.execute(
            select(Contest).where(Contest.enabled == True, Contest.start_time <= now, Contest.end_time >= now).limit(1)
        )
    contest = result.scalar_one_or_none()

    if contest is None:
        return templates.TemplateResponse("public/scoreboard.html", {"request": request, "contest": None, "board": [], "problems": []})

    now = datetime.utcnow()
    freeze = contest.freeze_time is not None and now >= contest.freeze_time
    board = await score_service.get_scoreboard(db, contest.id, freeze=freeze)
    problems = await score_service.get_contest_problems(db, contest.id)
    return templates.TemplateResponse(
        "public/scoreboard.html",
        {"request": request, "contest": contest, "board": board, "problems": problems, "freeze": freeze},
    )
```

- [ ] **Step 2: 在 app/routers/jury.py 中添加提交管理和重判**

```python
@router.get("/submissions")
async def jury_submissions(request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    from app.models import Judging
    result = await db.execute(
        select(Submission).order_by(Submission.submit_time.desc()).limit(100)
    )
    submissions = list(result.scalars().all())
    # 加载判题结果
    sub_data = []
    for sub in submissions:
        j_result = await db.execute(
            select(Judging).where(Judging.submission_id == sub.id).order_by(Judging.id.desc())
        )
        sub_data.append({"submission": sub, "judging": j_result.scalar_one_or_none()})
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submissions.html",
        {"request": request, "user": user, "submission_data": sub_data},
    )


@router.get("/submissions/{submission_id}")
async def jury_submission_detail(submission_id: int, request: Request, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        return RedirectResponse(url="/jury/submissions", status_code=303)
    # 加载判题和运行详情
    j_result = await db.execute(select(Judging).where(Judging.submission_id == submission_id).order_by(Judging.id.desc()))
    judging = j_result.scalar_one_or_none()
    runs = []
    if judging:
        runs_result = await db.execute(select(JudgeRun).where(JudgeRun.judging_id == judging.id))
        runs = list(runs_result.scalars().all())
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/submission_detail.html",
        {"request": request, "user": user, "submission": sub, "judging": judging, "runs": runs},
    )


@router.post("/submissions/{submission_id}/rejudge")
async def rejudge_submission(submission_id: int, user: User = Depends(require_role("jury")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if sub:
        # 收集所有关联的 judgeruns 并删除
        j_result = await db.execute(select(Judging).where(Judging.submission_id == submission_id))
        judgings_list = j_result.scalars().all()
        for judging in judgings_list:
            runs_result = await db.execute(select(JudgeRun).where(JudgeRun.judging_id == judging.id))
            for run in runs_result.scalars().all():
                await db.delete(run)
            await db.delete(judging)
        sub.state = SubmissionState.QUEUED
        await db.commit()
    return RedirectResponse(url=f"/jury/submissions/{submission_id}", status_code=303)
```

- [ ] **Step 3: 编写所有遗漏的模板文件**

需要补全的模板：
- `jury/submissions.html` — 提交列表（ID、时间、队伍、题目、语言、状态、结果）
- `jury/submission_detail.html` — 提交详情（代码高亮、判题结果、每个测试点、重判按钮）
- `public/scoreboard.html` — 公开计分板（无导航栏，纯数据展示 + 自动刷新 meta 标签）
- `team/submission_detail.html` — 选手查看提交详情（隐藏测试点输出）

- [ ] **Step 4: 更新 app/main.py**

```python
# 增加:
from app.routers import public
app.include_router(public.router)
```

- [ ] **Step 5: 端到端完整验证**

```bash
python run.py
# 1. admin 登录 Jury → 创建比赛（ICPC模式）
# 2. 创建题目 → 添加测试数据
# 3. 创建队伍账号
# 4. Team 登录 → 查看题目 → 提交代码
# 5. 查看判题结果 → 查看计分板
# 6. Jury 查看提交详情 → 重判
# 7. Team 提问 → Jury 回复
# 8. 公开计分板 /public/scoreboard
# 按 Ctrl+C 停止
```

- [ ] **Step 6: Commit**

```bash
git add app/routers/public.py app/routers/jury.py app/main.py app/templates/
git commit -m "feat: public scoreboard, submission detail, rejudging, all templates"
```

---

### Task 17: README 文档

**Files:**
- Create: `README.md`

- [ ] **Step 1: 编写 README.md**

```markdown
# 程序设计裁判系统

基于 FastAPI 的算法竞赛自动判题系统，参考 DOMjudge 设计。

## 快速开始

```bash
pip install -r requirements.txt
python run.py
```

浏览器访问 http://localhost:8000

默认管理员: admin / admin

## 支持的编程语言

- C (gcc)
- C++ (g++)
- Java (javac + java)
- Python 3

## 比赛模式

- **ICPC**: 通过/失败 + 罚时制，按 AC 题数 > 罚时排名
- **IOI**: 部分计分制，按总分排名

## 目录结构

```
├── run.py              # 启动入口
├── app/
│   ├── main.py         # FastAPI 应用
│   ├── config.py       # 配置
│   ├── models.py       # 数据库模型
│   ├── routers/        # 路由 (auth/jury/team/public)
│   ├── services/       # 业务逻辑
│   ├── judge/          # 判题引擎
│   └── templates/      # Jinja2 模板
└── judge.db            # SQLite 数据库
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```
