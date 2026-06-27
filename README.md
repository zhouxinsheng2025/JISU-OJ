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
