#!/usr/bin/env python3
"""
JISU OJ — Docker 部署脚本
用法: python deploy_docker.py

首次部署会自动 clone 仓库；后续部署执行 git pull。
"""
import paramiko
import sys
import time
import select

# ── 服务器信息 ──
HOST = "118.31.173.159"
PORT = 22
USER = "root"
PWD = "Zxs20060929@"
APP = "/opt/jisu-oj"
REPO = "https://github.com/zhouxinsheng2025/JISU-OJ.git"
IMAGE = "jisu-oj:latest"
CONTAINER = "jisu-oj"


def ssh_connect():
    """建立 SSH 连接"""
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USER, PWD, timeout=15)
    return c


def run(c, cmd, timeout=60):
    """执行远程命令，返回 stdout 字符串"""
    _, out, err = c.exec_command(cmd, timeout=timeout)
    out.channel.settimeout(timeout + 15)
    try:
        o = out.read().decode(errors="replace").strip()
    except Exception:
        o = ""
    try:
        e = err.read().decode(errors="replace").strip()
    except Exception:
        e = ""
    return o, e


def run_stream(c, cmd, timeout=300):
    """执行远程命令并流式输出（用于 Docker build 等长时间任务）"""
    _, out, err = c.exec_command(cmd, timeout=timeout)
    out.channel.settimeout(timeout + 60)
    try:
        while not out.channel.exit_status_ready:
            if out.channel.recv_ready():
                data = out.channel.recv(65536).decode(errors="replace")
                for line in data.split("\n"):
                    line = line.strip()
                    if line and ("Step" in line or "Successfully" in line or
                                 "error" in line.lower() or "DONE" in line):
                        print(f"  {line}")
            else:
                time.sleep(0.5)
        # Drain remaining
        rest = out.read().decode(errors="replace")
        if rest:
            for line in rest.strip().split("\n"):
                line = line.strip()
                if line:
                    print(f"  {line[:120]}")
    except Exception as ex:
        print(f"  [stream interrupted: {ex}]")
    e = err.read().decode(errors="replace").strip()
    if e and "warn" not in e.lower()[:30]:
        print(f"  [stderr] {e[:300]}")


# ── Main ──
print()
print("=" * 55)
print("  JISU OJ — Docker 部署")
print(f"  目标: {USER}@{HOST}:{PORT}")
print("=" * 55)
print()

c = ssh_connect()
print("[OK] SSH 已连接\n")

# ── 第1步：同步代码 ──
print("[1/6] 同步代码...")
o, e = run(c, f"""
if [ -d {APP}/.git ]; then
    cd {APP} && git pull origin main 2>&1
else
    echo "首次部署 — clone 仓库..."
    rm -rf {APP}
    git clone {REPO} {APP} 2>&1
fi
""", timeout=60)
print("  " + o.replace("\n", "\n  "))
if e:
    print(f"  [stderr] {e[:200]}")

# ── 第2步：检查 .env ──
print("\n[2/6] 检查 .env...")
o, e = run(c, f"""
cd {APP}
if [ ! -f .env ]; then
    cp .env.example .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "auto-generated-secret")
    echo "JWT_SECRET=$SECRET" >> .env
    echo ".env 已创建"
else
    echo ".env 已存在"
fi
""", timeout=15)
print("  " + o.replace("\n", "\n  "))

# ── 第3步：构建 Docker 镜像 ──
print("\n[3/6] 构建 Docker 镜像 (1-2分钟)...")
run_stream(c, f"cd {APP} && docker build -t {IMAGE} . 2>&1", timeout=300)
print("  [构建完成]")

# ── 第4步：停止旧容器，启动新容器 ──
print("\n[4/6] 重启容器...")
o, e = run(c, f"""
docker stop {CONTAINER} 2>/dev/null
docker rm {CONTAINER} 2>/dev/null
docker run -d --name {CONTAINER} --restart=always \\
  -p 80:8000 \\
  -v {APP}/data:/app/data \\
  -v {APP}/runs:/app/runs \\
  -v {APP}/judge.db:/app/judge.db \\
  -v {APP}/.env:/app/.env \\
  {IMAGE}
echo "容器已启动"
""", timeout=30)
print("  " + o.replace("\n", "\n  "))

# ── 第5步：等待启动 + 健康检查 ──
print("\n[5/6] 健康检查...")
time.sleep(5)
o, e = run(c, "curl -s http://localhost:80/health 2>&1", timeout=15)
print(f"  Health: {o}")

# ── 第6步：查看容器状态和日志 ──
print("\n[6/6] 容器状态...")
o, e = run(c, f"docker ps --filter name={CONTAINER} --format '{{{{.Names}}}}  {{{{.Status}}}}  {{{{.Ports}}}}'", timeout=10)
print(f"  {o}")
print()
o, e = run(c, f"docker logs --tail 15 {CONTAINER} 2>&1", timeout=10)
if o:
    print("  启动日志:")
    for line in o.split("\n")[:12]:
        print(f"    {line[:150]}")

c.close()
print()
print("=" * 55)
print("  部署完成！")
print(f"  访问: http://{HOST}/")
print(f"  健康: http://{HOST}/health")
print("=" * 55)
