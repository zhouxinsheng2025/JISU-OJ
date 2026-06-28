#!/bin/bash
# JISU裁判系统 — 一键部署脚本
set -e

echo "=== JISU程序设计裁判系统 部署 ==="

# 检查Python版本
python3 --version || { echo "需要Python 3.10+"; exit 1; }

# 安装依赖
echo "[1/4] 安装依赖..."
pip3 install -r requirements.txt -q

# 生成JWT密钥
echo "[2/4] 生成配置..."
if [ ! -f .env ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cp .env.example .env
    sed -i "s/change-me-in-production/$SECRET/" .env
    echo "  .env 已生成，JWT密钥已随机设置"
else
    echo "  .env 已存在，跳过"
fi

# 创建目录
echo "[3/4] 创建目录..."
mkdir -p runs data/testcases

# 启动服务
echo "[4/4] 启动服务..."
echo ""
echo "  部署完成！启动方式："
echo ""
echo "  # 开发模式："
echo "  python3 run.py"
echo ""
echo "  # 生产模式（推荐）："
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
echo ""
echo "  # 或使用 systemd（见 jisu-oj.service）"
echo ""
echo "  访问 http://服务器IP:8000"
echo "  默认管理员: admin / admin"
