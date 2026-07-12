#!/usr/bin/env python3
"""Docker deploy to Alibaba Cloud 118.31.173.159"""
import paramiko, time, sys

HOST, PORT, USER, PWD = "118.31.173.159", 22, "root", "Zxs20060929@"
APP = "/opt/jisu-oj"
IMAGE = "jisu-oj:latest"
CONTAINER = "jisu-oj"

CMDS = [
    # 1. Pull latest code
    (f"cd {APP} && git pull origin main 2>&1", "Git pull"),

    # 2. Ensure .env exists
    (f"cd {APP} && [ -f .env ] || (cp .env.example .env && "
     "python3 -c \"import secrets; print('JWT_SECRET=' + secrets.token_hex(32))\" >> .env && echo '.env created')",
     "Check .env"),

    # 3. Build Docker image
    (f"cd {APP} && docker build -t {IMAGE} . 2>&1", "Build image (1-2 min)"),

    # 4. Stop & remove old container
    (f"docker stop {CONTAINER} 2>/dev/null; docker rm {CONTAINER} 2>/dev/null; echo 'old container cleaned'",
     "Clean old container"),

    # 5. Start new container
    (f"docker run -d --name {CONTAINER} --restart=always "
     f"-p 80:8000 "
     f"-v {APP}/data:/app/data "
     f"-v {APP}/runs:/app/runs "
     f"-v {APP}/judge.db:/app/judge.db "
     f"-v {APP}/.env:/app/.env "
     f"{IMAGE}",
     "Start container"),

    # 6. Health check
    ("sleep 4 && docker logs --tail 20 jisu-oj 2>&1", "Startup logs"),
    ("curl -s http://localhost:80/health 2>&1", "Health check"),
    ("docker ps --filter name=jisu-oj --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "Container status"),
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("\n" + "="*55)
print("  JISU OJ - Docker Deploy")
print(f"  Target: {USER}@{HOST}:{PORT}")
print("="*55 + "\n")

try:
    c.connect(HOST, PORT, USER, PWD, timeout=15)
except Exception as e:
    print(f"[FAIL] SSH connect: {e}")
    sys.exit(1)

print("[OK] SSH connected\n")

for i, (cmd, label) in enumerate(CMDS):
    print(f"[{i+1}/{len(CMDS)}] {label}...")
    _, out, err = c.exec_command(cmd, timeout=300)
    o = out.read().decode(errors='replace').strip()
    e = err.read().decode(errors='replace').strip()
    if o:
        lines = o.split('\n')
        if len(lines) > 20:
            o = '\n'.join(lines[:20]) + f"\n... (truncated, {len(lines)} lines total)"
        print("  " + o.replace('\n', '\n  '))
    if e and 'warn' not in e.lower()[:50]:
        print("  [stderr] " + e[:300].replace('\n', '\n  '))
    print()

c.close()
print("="*55)
print("  Deploy complete!")
print(f"  Visit: http://{HOST}/")
print(f"  Health: http://{HOST}/health")
print("="*55)
