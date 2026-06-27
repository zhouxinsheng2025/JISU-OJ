# 程序设计裁判系统 — 设计规格书

**日期：** 2026-06-27  
**参考：** DOMjudge (https://www.domjudge.org)  
**状态：** 待审核

---

## 1. 项目概述

一个基于 Python 全栈的算法竞赛自动判题 Web 系统。参考 DOMjudge 的架构思想，采用更轻量的技术栈，目标是快速开发、易于维护、单机部署。

### 1.1 适用场景

- 中小规模算法编程竞赛（ACM/ICPC赛制、IOI赛制）
- 教学场景（课堂练习、期末考试）
- 校内选拔赛

### 1.2 技术栈

| 层 | 技术 |
|---|---|
| **Web 框架** | FastAPI (Python 3.10+) |
| **模板引擎** | Jinja2 |
| **CSS 框架** | Tailwind CSS (CDN) |
| **数据库** | SQLite（可迁移至 PostgreSQL） |
| **ORM** | SQLAlchemy |
| **判题执行** | subprocess + psutil 资源限制 |
| **部署** | uvicorn 单进程 |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI 应用                       │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Team 界面 │  │ Jury 界面 │  │  Public 界面     │   │
│  │ 提交/查看 │  │ 管理/判题 │  │  计分板          │   │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       │             │               │                │
│  ┌────┴─────────────┴───────────────┴────────────┐  │
│  │              REST API 路由层                    │  │
│  └────────────────────┬───────────────────────────┘  │
│                       │                              │
│  ┌────────────────────┼───────────────────────────┐  │
│  │              业务逻辑层                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │  │
│  │  │ 用户管理  │  │ 比赛管理  │  │  计分服务    │  │  │
│  │  └──────────┘  └──────────┘  └─────────────┘  │  │
│  └────────────────────┬───────────────────────────┘  │
│                       │                              │
│  ┌────────────────────┼───────────────────────────┐  │
│  │              SQLite 数据库                       │  │
│  └────────────────────┴───────────────────────────┘  │
│                                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │         判题引擎 (Judge Engine)                 │  │
│  │  asyncio后台任务轮询 → 编译 → 执行 → 比对 → 写结果│  │
│  │  subprocess + 资源限制 (psutil)                 │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 2.2 核心设计决策

- **判题引擎内嵌**于 FastAPI 进程中（后台 asyncio 任务），无需额外进程通信
- **三种角色**：Jury（裁判/管理员）、Team（选手）、Public（公开计分板）
- **轮询式判题**：判题引擎定时扫描待判提交，按 FIFO 顺序处理
- **SQLite** 单文件，FastAPI 启动时自动建表
- **沙箱**：基础模式 — subprocess 执行 + 超时/内存限制，适用受信任用户的内网比赛

---

## 3. 数据模型

### 3.1 ER 图

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│   users   │       │   contests   │       │   problems   │
├──────────┤       ├──────────────┤       ├──────────────┤
│ id       │──┐    │ id           │──┐    │ id           │
│ username │  │    │ title        │  │    │ contest_id   │──┐
│ password │  │    │ start_time   │  │    │ title        │  │
│ teamname │  │    │ end_time     │  │    │ time_limit   │  │
│ role     │  │    │ score_mode   │  │    │ memory_limit │  │
│ enabled  │  │    │ freeze_time  │  │    │ order        │  │
└──────────┘  │    │ enabled      │  │    └──────────────┘  │
              │    └──────────────┘  │                       │
              │                      │    ┌──────────────┐  │
              │  ┌───────────────────┘    │  testcases   │  │
              │  │                        ├──────────────┤  │
              │  │   ┌──────────────┐     │ id           │  │
              │  │   │ submissions  │     │ problem_id   │──┘
              │  │   ├──────────────┤     │ input        │
              │  ├──←│ contest_id   │     │ output       │
              │  │   │ problem_id   │     │ is_sample    │
              │  │   │ team_id      │──┐  └──────────────┘
              │  │   │ language     │  │
              │  │   │ source_code  │  │  ┌──────────────┐
              │  │   │ submit_time  │  │  │  judgeruns   │
              │  │   │ state        │  │  ├──────────────┤
              │  │   └──────────────┘  │  │ judging_id   │──┐
              │  │                     │  │ testcase_id  │  │
              │  │   ┌──────────────┐  │  │ result       │  │
              │  │   │  judgings    │  │  │ runtime      │  │
              │  │   ├──────────────┤  │  │ output       │  │
              │  │   │ submission_id│──┘  └──────────────┘  │
              │  │   │ result       │                       │
              │  │   │ score        │    ┌──────────────┐  │
              │  │   │ started      │    │clarifications│  │
              │  └──←│ ended        │    ├──────────────┤  │
              │      └──────────────┘    │ contest_id   │──┤
              │                          │ sender_id    │  │
              └──────────────────────────│ recipient_id │  │
                                         │ question     │  │
                                         │ answer       │  │
                                         └──────────────┘  │
                                                           │
  ┌──────────────┐                                        │
  │  scoreboard  │  (缓存表)                               │
  ├──────────────┤                                        │
  │ contest_id   │──┘
  │ team_id      │
  │ problem_id   │
  │ submissions  │
  │ total_time   │
  │ is_correct   │
  └──────────────┘
```

### 3.2 各表职责

| 表名 | 说明 |
|---|---|
| **users** | 用户，role 分 `jury`(裁判/管理)、`team`(选手) |
| **contests** | 比赛配置，score_mode 为 `icpc`/`ioi`，freeze_time 为封榜时间 |
| **problems** | 赛题，含时限、内存限制，属于某场比赛 |
| **testcases** | 测试数据，分样本(is_sample)和隐藏数据 |
| **submissions** | 提交记录，state 流转: `queued → judging → done` |
| **judgings** | 判题总结果，关联所有测试点运行 |
| **judgeruns** | 每个测试点的运行详情（耗时、输出、判题结果） |
| **clarifications** | 选手与裁判间问答 |
| **scoreboard** | 计分板缓存，避免每次实时计算 |

### 3.3 关键字段枚举

- **users.role**: `jury` | `team`
- **contests.score_mode**: `icpc` | `ioi`
- **submissions.state**: `queued` | `judging` | `done`
- **submissions.language**: `c` | `cpp` | `python` | `java`
- **judgings.result / judgeruns.result**: `AC` | `WA` | `TLE` | `MLE` | `RTE` | `OLE` | `CE` | `PE`

---

## 4. 判题流程

### 4.1 流程概述

```
选手提交代码
     │
     ▼
┌─────────────────┐
│  1. 接收提交     │  存入 submissions 表, state=queued
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 判题引擎取件  │  后台 asyncio task 每1秒扫描 pending 提交
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. 编译代码     │  写入临时目录, subprocess 调用编译器
│   (Compiler)    │  ── 失败 → Compiler Error, 结束
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 运行测试点   │  逐个测试点执行, 捕获 stdout/stderr
│   (Runner)      │  超时/超内存/运行时错误 → 对应判题结果
│                 │  逐点比对输出(diff) → AC 或 WA
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. 汇总结果     │  ICPC: 全AC才AC, 第一个失败即停止(懒判)
│   (Scorer)      │  IOI: 每个测试点计分, 取总分
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. 更新结果     │  写 judgings / judgeruns 表
│                 │  刷新 scoreboard 缓存
│                 │  state=done, 选手可见
└─────────────────┘
```

### 4.2 判题结果类型 (Verdict)

| 结果 | 缩写 | 说明 |
|---|---|---|
| Correct | **AC** | 答案正确 |
| Wrong Answer | **WA** | 输出与预期不符 |
| Time Limit Exceeded | **TLE** | 超过时间限制 |
| Memory Limit Exceeded | **MLE** | 超过内存限制 |
| Runtime Error | **RTE** | 运行崩溃/异常退出 |
| Output Limit Exceeded | **OLE** | 输出超过限制 |
| Compiler Error | **CE** | 编译失败 |
| Presentation Error | **PE** | 格式错误（可选，首次实现可暂不支持） |

### 4.3 ICPC 计分规则

- 每道题只有 **AC / 未通过** 两种状态
- AC 时间 = 比赛开始到 AC 提交的分钟数
- 罚时 = 每次未通过提交罚 20 分钟（AC 后才计入）
- 排名：先比 AC 题数，再比总罚时（罚时少排前面）

### 4.4 IOI 计分规则

- 每题多个测试点，每个测试点独立计分
- 最终得分 = 各测试点得分之和
- 排名：按总得分降序
- 提交多次取最高分

### 4.5 安全限制

- 编译超时：30 秒
- 源码大小限制：256 KB
- 输出大小限制：8 MB
- 使用 psutil 限制子进程内存

---

## 5. 界面设计

### 5.1 Team 界面（选手端）

| 页面 | 路径 | 功能 |
|---|---|---|
| 登录页 | `/team/login` | 用户名+密码登录 |
| 仪表盘 | `/team/` | 当前比赛概览、倒计时、个人提交统计 |
| 题目列表 | `/team/problems` | 查看所有题目，点击进入详情 |
| 题目详情 | `/team/problems/{id}` | 题目描述、输入输出说明、样例数据、提交入口 |
| 提交代码 | (题目详情内嵌) | 代码粘贴/文件上传 + 语言选择 |
| 提交记录 | `/team/submissions` | 自己所有提交的状态列表，实时刷新 |
| 计分板 | `/team/scoreboard` | 查看实时排名 |
| 问答 | `/team/clarifications` | 向裁判提问，查看回复 |

### 5.2 Jury 界面（裁判/管理员端）

| 页面 | 路径 | 功能 |
|---|---|---|
| 登录页 | `/jury/login` | 管理员登录 |
| 仪表盘 | `/jury/` | 系统概览：提交数、判题队列、判题机状态 |
| 比赛管理 | `/jury/contests` | 创建/编辑/启用比赛 |
| 题目管理 | `/jury/contests/{id}/problems` | 添加/编辑题目、上传测试数据 |
| 测试数据 | `/jury/problems/{id}/testcases` | 管理测试点，支持批量导入 |
| 提交列表 | `/jury/submissions` | 所有提交，可按状态/题目/队伍筛选 |
| 提交详情 | `/jury/submissions/{id}` | 查看代码、判题结果、每个测试点详情、手动重判 |
| 重判 | (提交详情内) | 对单个提交或整题重判 |
| 队伍管理 | `/jury/teams` | 增删改参赛队伍 |
| 问答处理 | `/jury/clarifications` | 回复选手提问，发布公告 |
| 计分板 | `/jury/scoreboard` | 完整计分板（包括封榜期间真实排名） |

### 5.3 Public 界面（公开）

| 页面 | 路径 | 功能 |
|---|---|---|
| 公开计分板 | `/public/scoreboard` | 只读计分板，可设置自动刷新 |

### 5.4 界面风格

- **模板渲染**：Jinja2 模板 + Tailwind CSS CDN，无前端框架
- **Team 界面**：深色背景 + 代码风格配色
- **Jury 界面**：浅色背景 + 信息密度高
- **移动端适配**：Tailwind 响应式，手机也可提交代码

---

## 6. 项目结构

```
judge-system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口 + 事件处理
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接 + 建表
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 数据校验
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # 登录认证
│   │   ├── team.py          # 选手端路由
│   │   ├── jury.py          # 裁判端路由
│   │   └── public.py        # 公开路由
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py  # 认证逻辑
│   │   ├── contest_service.py
│   │   ├── submission_service.py
│   │   └── score_service.py # 计分计算
│   │
│   ├── judge/
│   │   ├── __init__.py
│   │   ├── engine.py        # 判题引擎（后台任务）
│   │   ├── compiler.py      # 编译模块
│   │   ├── runner.py        # 执行模块
│   │   └── scorer.py        # 计分/比对
│   │
│   ├── templates/           # Jinja2 模板
│   │   ├── base.html
│   │   ├── team/
│   │   ├── jury/
│   │   └── public/
│   │
│   └── static/              # 静态文件
│       ├── css/
│       └── js/
│
├── data/                    # 测试数据存储（运行时生成）
│   └── testcases/
│
├── runs/                    # 判题临时目录
│
├── judge.db                 # SQLite 数据库文件
├── requirements.txt
├── run.py                   # 启动脚本
└── README.md
```

---

## 7. 认证与权限

- **JWT Token**：登录后签发，存入 Cookie
- **角色分离**：Jury 路由需要 `role=jury`，Team 路由需要 `role=team`
- **比赛隔离**：Team 只能看自己参加的比赛的题目和提交
- **Public 界面**：无需登录

---

## 8. 非功能需求

| 类别 | 要求 |
|---|---|
| **性能** | 支持 100 支队伍、每秒 5 次提交的并发量 |
| **判题延迟** | 提交到开始判题 < 2 秒（正常负载下） |
| **数据安全** | 密码 bcrypt 哈希；隐藏测试数据不可见 |
| **可用性** | 单进程部署，一条命令启动 |
| **浏览器兼容** | 现代浏览器（Chrome/Firefox/Edge 近两年版本） |

---

## 9. 后续扩展（非首次实现范围）

- Docker 沙箱隔离
- 分布式判题机（多 Judgehost）
- PostgreSQL 数据库支持
- 代码相似度检测（反作弊）
- WebSocket 实时推送判题结果
- 气球通知打印（Balloon）
- 命令行提交工具
