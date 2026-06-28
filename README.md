<p align="center">
  <img src="app/static/emblem.webp" width="80" alt="JISU OJ">
</p>

<h1 align="center">JISU程序设计裁判系统</h1>

<p align="center">
  吉林外国语大学 · 程序设计竞赛自动判题平台<br>
  专为 ACM 集训队日常训练和竞赛场景打造
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Tailwind-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs">
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#功能特性">功能特性</a> ·
  <a href="#使用指南">使用指南</a> ·
  <a href="#项目结构">项目结构</a> ·
  <a href="#部署">部署</a>
</p>

---

## ✨ 功能特性

| 模块 | 功能 |
|---|---|
| ⚡ **自动判题** | 提交即判，支持 C / C++ / Java / Python，subprocess 隔离执行 |
| 📚 **题库系统** | 题目独立管理，难度分级（简单/中等/困难）+ 算法标签 |
| 🏆 **比赛模式** | ICPC 罚时制 + IOI 分数制，实时计分板，支持封榜 |
| 🏋 **开放练习** | 不限时刷题，自动追踪个人进度（AC 数、提交数、首次通过时间） |
| 📝 **作业模式** | 限时作业，比比赛更灵活的时间约束 |
| 📦 **ZIP 导入** | 批量上传测试数据，兼容 DOMjudge problem format |
| 📥 **CSV 导入** | 一键批量导入全队学生名单 |
| 🔄 **重判机制** | 修改测试数据后可对单个提交或整题重新判题 |
| 📊 **实时排名** | ICPC（解题数→罚时）/ IOI（总分），自动刷新 |
| 💬 **问答系统** | 选手提交疑问 → 裁判回复，支持公开/私密 |
| 📱 **响应式设计** | 手机、平板、桌面均可正常使用 |
| 🐳 **Docker 部署** | 提供 Dockerfile，一行命令部署 |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip

### 本地运行

```bash
git clone https://github.com/zhouxinsheng2025/JISU-OJ.git
cd JISU-OJ

pip install -r requirements.txt
mkdir -p runs
python run.py
```

浏览器打开 **http://localhost:8000**，管理员账号由系统首次启动自动创建。

### Docker 部署

```bash
docker build -t jisu-oj .
docker run -d -p 8000:8000 jisu-oj
```

### 生产部署

```bash
cp .env.example .env
# 编辑 .env，设置 JWT_SECRET

nohup uvicorn app.main:app --host 0.0.0.0 --port 80 > server.log 2>&1 &
```

## 📖 使用指南

### 管理员

```
1. 题库管理 → 新建题目（含测试数据 ZIP 上传）
2. 队伍管理 → 单个创建 或 CSV 批量导入
3. 比赛管理 → 新建比赛/练习/作业 → 从题库选题
4. 监控提交 → 查看/重判所有提交
```

### 选手

```
1. 登录 → 有比赛进入比赛面板，无比赛进入开放练习
2. 选择题目 → 查看描述和样例 → 写代码提交
3. 查看 Status 判题结果 → Rank 计分板排名
```

### 判题结果

| 结果 | 含义 |
|---|---|
| ✅ AC | 答案正确 |
| ❌ WA | 输出错误 |
| ⏱ TLE | 超时 |
| 💾 MLE | 超内存 |
| 💥 RTE | 运行时错误 |
| ⚙ CE | 编译错误 |

### 测试数据格式（兼容 DOMjudge）

```
testdata.zip
├── sample/1.in, 1.out    ← 选手可见样例
└── secret/1.in, 1.out    ← 隐藏判题数据
```

### CSV 批量导入队伍

```csv
username,password,teamname
zhangsan,123456,张三
lisi,123456,李四
```

## 📁 项目结构

```
JISU-OJ/
├── run.py                    # 开发启动
├── deploy.sh                 # 生产部署脚本
├── Dockerfile                # Docker 构建
├── jisu-oj.service           # systemd 配置
├── requirements.txt
├── .env.example
│
├── app/
│   ├── main.py               # 应用入口
│   ├── config.py             # 配置（.env 支持）
│   ├── database.py           # 异步 SQLAlchemy
│   ├── models.py             # 13 张表 ORM
│   ├── schemas.py            # Pydantic 校验
│   ├── dependencies.py       # 认证中间件
│   │
│   ├── routers/
│   │   ├── auth.py           # 登录认证
│   │   ├── jury.py           # 管理端
│   │   ├── team.py           # 选手端
│   │   └── public.py         # 公开计分板
│   │
│   ├── services/
│   │   ├── auth_service.py   # bcrypt + JWT
│   │   ├── contest_service.py
│   │   ├── submission_service.py
│   │   ├── score_service.py  # 计分算法
│   │   └── testcase_service.py # ZIP 解析
│   │
│   ├── judge/
│   │   ├── engine.py         # 判题引擎
│   │   ├── compiler.py       # 编译
│   │   ├── runner.py         # 执行 & 资源限制
│   │   └── scorer.py         # 输出比对
│   │
│   ├── templates/            # Jinja2 模板
│   └── static/               # 校徽等静态资源
│
├── runs/                     # 判题临时目录
└── data/                     # 测试数据存储
```

## 🗄 数据库表

| 表 | 说明 |
|---|---|
| `users` | 用户（管理员 + 队伍） |
| `problems` | 题库（PID、难度、标签） |
| `contests` | 比赛（比赛/练习/作业） |
| `contest_problems` | 比赛↔题目关联 |
| `testcases` | 测试数据 |
| `submissions` | 提交记录 |
| `judgings` | 判题结果 |
| `judgeruns` | 逐测试点详情 |
| `scoreboard` | 计分板缓存 |
| `clarifications` | 问答 |
| `user_progress` | 刷题进度 |

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 框架 | FastAPI (async) |
| 数据库 | SQLite / PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| 前端 | Jinja2 + Tailwind CSS |
| 认证 | bcrypt + JWT |
| 判题 | subprocess + psutil |

## 📄 License

MIT © 吉林外国语大学
