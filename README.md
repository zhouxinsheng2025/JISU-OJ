# JISU程序设计裁判系统

> 吉林外国语大学 · 程序设计竞赛自动判题系统  
> 参考 [DOMjudge](https://www.domjudge.org) 架构设计，专为集训队日常训练和比赛场景打造

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 功能特性

- ⚡ **自动判题** — 提交即判，支持 C / C++ / Java / Python
- 📚 **题库系统** — 题目独立管理，难度分级 + 算法标签
- 🏆 **比赛模式** — ICPC 罚时制 + IOI 分数制，实时计分板
- 🏋 **开放练习** — 不限时刷题，自动追踪个人进度
- 📝 **作业模式** — 限时作业，灵活宽松
- 📦 **ZIP导入** — 测试数据批量上传，兼容 DOMjudge 格式
- 📥 **CSV导入** — 一键导入全队学生名单
- 🔄 **重判机制** — 修改测试数据后可重判所有提交
- 📊 **计分板** — ICPC/IOI 双排名，支持封榜
- 💬 **问答系统** — 选手提问 ↔ 裁判回复
- 📱 **响应式** — 手机也能提交代码
- 🐳 **Docker 部署** — 一行命令即可部署

## 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p runs

# 启动服务
python run.py
```

浏览器打开 **http://localhost:8000**

**默认管理员：** `admin` / `admin`

### Docker 部署

```bash
docker build -t jisu-oj .
docker run -d -p 8000:8000 jisu-oj
```

### 生产部署

```bash
# 安装依赖
pip install -r requirements.txt

# 复制并修改配置
cp .env.example .env
# 编辑 .env，设置 JWT_SECRET 为随机字符串

# 后台启动
nohup uvicorn app.main:app --host 0.0.0.0 --port 80 > server.log 2>&1 &
```

## 使用指南

### 管理员操作流程

```
1. 题库管理 (/jury/bank)
   ├── 新建题目：标题、描述、难度(简单/中等/困难)、标签(DP,图论,贪心...)
   ├── 上传测试数据：ZIP 文件（sample/ 样例, secret/ 隐藏）
   └── 题目独立于比赛，可复用
   
2. 队伍管理 (/jury/teams)
   ├── 单个创建（用户名、密码、队伍名）
   ├── CSV 批量导入：username,password,teamname
   └── 启用/禁用/删除
   
3. 比赛管理 (/jury/contests)
   ├── 类型：比赛(限时) / 练习(不限时) / 作业
   ├── 选题：从题库挑选题目加入比赛
   └── 计分模式：ICPC / IOI
   
4. 监控 (/jury/submissions)
   ├── 查看所有提交
   ├── 判题详情（代码、每测试点耗时/结果）
   └── 手动重判
```

### 选手使用流程

```
1. 登录 → 仪表盘
   ├── 有比赛 → 比赛面板 + 倒计时
   └── 无比赛 → 开放练习

2. 做题
   ├── 查看题目（描述、样例、时限）
   ├── 选择语言 → 粘贴代码 → 提交
   └── 实时查看判题结果

3. 查看
   ├── Status → 自己的提交记录和结果
   ├── Rank → 实时计分板
   └── Clarification → 向裁判提问
```

## 支持的编程语言

| 语言 | 编译器/解释器 | 说明 |
|---|---|---|
| **C** | gcc -O2 | C11 |
| **C++** | g++ -O2 | C++17 |
| **Java** | javac + java | 类名需为 Main |
| **Python** | python3 | 直接解释执行 |

## 判题结果说明

| 结果 | 缩写 | 说明 |
|---|---|---|
| ✅ Correct | AC | 答案正确 |
| ❌ Wrong Answer | WA | 输出与预期不符 |
| ⏱ Time Limit Exceeded | TLE | 超过时间限制 |
| 💾 Memory Limit Exceeded | MLE | 超过内存限制 |
| 💥 Runtime Error | RTE | 运行崩溃或异常退出 |
| 📤 Output Limit Exceeded | OLE | 输出超过限制 |
| ⚙ Compiler Error | CE | 编译失败 |

## 测试数据 ZIP 格式

参照 DOMjudge 标准：

```
testdata.zip
├── sample/          ← 选手可见样例
│   ├── 1.in
│   └── 1.out
└── secret/          ← 隐藏判题数据
    ├── 1.in
    ├── 1.out
    ├── 2.in
    └── 2.out
```

系统自动配对 `.in`/`.out`（或 `.in`/`.ans`），按文件名数字排序。

## CSV 队伍导入格式

```csv
username,password,teamname
zhangsan,123456,张三
lisi,123456,李四
wangwu,123456,王五
```

## 计分规则

### ICPC 模式（ACM 赛制）
- 每题只有通过/未通过两种状态
- AC 时间 = 比赛开始到首次 AC 的分钟数
- 罚时 = 每次未通过提交罚 20 分钟
- 排名：先比 AC 题数，再比总罚时

### IOI 模式（OI 赛制）
- 每题多个测试点，各自独立计分
- 每题得分 = AC 测试点数 / 总测试点数 × 100
- 排名：按总得分降序

## 项目结构

```
├── run.py                     # 开发模式启动入口
├── deploy.sh                  # 生产部署脚本
├── Dockerfile                 # Docker 构建文件
├── jisu-oj.service           # systemd 服务文件
├── requirements.txt           # Python 依赖
├── .env.example               # 配置文件模板
│
├── app/
│   ├── main.py                # FastAPI 应用入口 + 种子数据
│   ├── config.py              # 配置管理（支持 .env）
│   ├── database.py            # SQLAlchemy 异步引擎
│   ├── models.py              # 13 张表的 ORM 模型
│   ├── schemas.py             # Pydantic 请求/响应校验
│   ├── dependencies.py        # 认证中间件
│   ├── templates_helpers.py   # Jinja2 模板引擎
│   │
│   ├── routers/
│   │   ├── auth.py            # 登录/登出
│   │   ├── jury.py            # 裁判端（题库/比赛/队伍/提交）
│   │   ├── team.py            # 选手端（做题/提交/练习）
│   │   └── public.py          # 公开计分板
│   │
│   ├── services/
│   │   ├── auth_service.py    # bcrypt 哈希 + JWT 签发
│   │   ├── contest_service.py # 比赛 CRUD + 选题
│   │   ├── submission_service.py
│   │   ├── score_service.py   # 计分板计算
│   │   └── testcase_service.py # ZIP 测试数据解析
│   │
│   ├── judge/
│   │   ├── engine.py          # 判题引擎（后台轮询）
│   │   ├── compiler.py        # 编译模块
│   │   ├── runner.py          # 执行模块（资源限制）
│   │   └── scorer.py          # 输出比对 + 评分
│   │
│   ├── templates/             # Jinja2 模板（22个）
│   │   ├── auth/              # 登录页
│   │   ├── jury/              # 裁判端页面
│   │   ├── team/              # 选手端页面
│   │   └── public/            # 公开计分板
│   │
│   └── static/                # 静态资源（校徽等）
│       └── emblem.webp
│
├── runs/                      # 判题临时工作目录
└── data/testcases/            # 测试数据文件存储
```

## 数据库模型

| 表名 | 说明 |
|---|---|
| `users` | 用户（管理员 + 参赛队伍） |
| `contests` | 比赛（比赛/练习/作业） |
| `problems` | 题库（独立于比赛） |
| `contest_problems` | 比赛-题目多对多关联 |
| `testcases` | 测试数据 |
| `submissions` | 提交记录 |
| `judgings` | 判题总结果 |
| `judgeruns` | 每个测试点的运行详情 |
| `scoreboard` | 计分板缓存 |
| `clarifications` | 选手↔裁判问答 |
| `user_progress` | 个人刷题进度 |

## 环境变量

复制 `.env.example` 为 `.env` 进行配置：

```bash
DATABASE_URL=sqlite+aiosqlite:///judge.db   # 数据库
JWT_SECRET=your-random-secret-here           # JWT 密钥（务必修改）
JWT_EXPIRE_HOURS=24                          # 登录有效期
JUDGE_POLL_INTERVAL=1                        # 判题引擎轮询间隔(秒)
COMPILE_TIME_LIMIT=30                        # 编译超时(秒)
```

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI |
| 数据库 | SQLite（可迁移 PostgreSQL） |
| ORM | SQLAlchemy 2.0 (async) |
| 模板引擎 | Jinja2 |
| CSS | Tailwind CSS CDN |
| 认证 | bcrypt + JWT |
| 判题隔离 | subprocess + psutil |

## License

MIT © 吉林外国语大学
