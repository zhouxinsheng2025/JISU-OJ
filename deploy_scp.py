#!/usr/bin/env python3
"""JISU OJ — SCP + 直接运行部署"""
import os, sys, time, tarfile, paramiko

HOST, PORT, USER, PWD = "118.31.173.159", 22, "root", "Zxs20060929@"
APP = "/opt/jisu-oj"
PY = "python3.11"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TARBALL = os.path.join(PROJECT_DIR, "deploy.tar.gz")
EXCLUDE = {".git", "__pycache__", ".pytest_cache", ".claude", "runs"}

def step(label):
    print(f"\n{'='*50}\n  {label}\n{'='*50}")

def ssh_cmd(c, cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    out.channel.settimeout(timeout + 15)
    try: o = out.read().decode(errors="replace")
    except: o = ""
    try: e = err.read().decode(errors="replace").strip()
    except: e = ""
    if o.strip(): print(o.strip())
    if e and "warn" not in e.lower()[:30]: print("[stderr]", e[:300])
    return o

# 1. 打包
step("1/5 Pack")
with tarfile.open(TARBALL, "w:gz") as tar:
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE and not d.endswith(".egg-info")]
        for f in files:
            if f.endswith((".pyc", ".pyo")) or f == "judge.db": continue
            full = os.path.join(root, f)
            tar.add(full, arcname=os.path.relpath(full, PROJECT_DIR))
kb = os.path.getsize(TARBALL) / 1024
print(f"  deploy.tar.gz: {kb:.0f} KB")

# 2. 连接 + 上传
step("2/5 Upload")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PWD, timeout=15)
print("  SSH connected")
sftp = c.open_sftp()
sftp.put(TARBALL, "/tmp/deploy.tar.gz")
sftp.close()
print(f"  Uploaded ({kb:.0f} KB)")

# 3. 解压 + 保留 .env
step("3/5 Extract & Setup")
ssh_cmd(c, f"""
# backup .env
if [ -f {APP}/.env ]; then cp {APP}/.env /tmp/jisu_env_backup; echo ".env backed up"; fi
# clean & extract
rm -rf {APP}; mkdir -p {APP}
cd {APP} && tar -xzf /tmp/deploy.tar.gz && echo "extracted"
# restore or create .env
if [ -f /tmp/jisu_env_backup ]; then
    cp /tmp/jisu_env_backup {APP}/.env && echo ".env restored"
elif [ -f {APP}/.env.example ]; then
    cp {APP}/.env.example {APP}/.env
    S=$({PY} -c "import secrets;print(secrets.token_hex(32))" 2>/dev/null || echo "auto-secret")
    echo "JWT_SECRET=$S" >> {APP}/.env
    echo ".env created"
fi
mkdir -p {APP}/runs {APP}/data/testcases
echo "dirs ready"
""")

# 4. 安装依赖 + 停止旧服务 + 启动新服务（gunicorn 多进程）
step("4/5 Install & Restart")
print("  installing deps...")
ssh_cmd(c, f"cd {APP} && {PY} -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -5", timeout=180)
print("  stopping old...")
ssh_cmd(c, "fuser -k 80/tcp 2>/dev/null; sleep 2; echo 'old stopped'", timeout=10)
print("  starting gunicorn (4 workers)...")
ssh_cmd(c, f"cd {APP} && nohup {PY} -m gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:80 --timeout 120 --access-logfile - --error-logfile - > server.log 2>&1 < /dev/null & echo 'started'", timeout=10)
time.sleep(5)

# 5. 验证
step("5/5 Verify")
ssh_cmd(c, "echo '--- Health ---' && curl -s http://localhost:80/health")
ssh_cmd(c, "echo '--- Workers ---' && ps aux | grep -E 'gunicorn|uvicorn' | grep -v grep | wc -l && echo 'processes running'")
ssh_cmd(c, f"echo '--- Log (tail) ---' && cd {APP} && tail -15 server.log")

c.close()
os.remove(TARBALL)
print(f"\n{'='*50}\n  Done! http://{HOST}/\n{'='*50}")
