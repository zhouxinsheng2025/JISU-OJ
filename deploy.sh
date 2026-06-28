#!/bin/bash
# JISU裁判系统 — 腾讯云轻量服务器部署脚本
set -e

echo "========================================="
echo "  吉林外国语大学 程序设计裁判系统 部署"
echo "========================================="

# 检查Python
python3 --version || { echo "❌ 需要Python3.10+"; exit 1; }

# 安装依赖
echo "[1/3] 安装Python依赖..."
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建目录
echo "[2/3] 初始化..."
mkdir -p runs data/testcases
if [ ! -f .env ]; then
    cp .env.example .env
    # 生成随机密钥
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-me-in-production/$SECRET/" .env
    echo "  .env 已生成（JWT密钥已随机设置）"
fi

# 安装编译器(判题用)
echo "[3/3] 检查编译环境..."
which gcc >/dev/null 2>&1 || { echo "  安装gcc..."; sudo apt-get install -y gcc g++ 2>/dev/null || echo "  跳过(请手动安装)"; }
which python3 >/dev/null 2>&1 || echo "  请安装python3"

echo ""
echo "========================================="
echo "  部署完成！启动命令："
echo ""
echo "  生产模式(推荐):"
echo "    nohup uvicorn app.main:app --host 0.0.0.0 --port 80 > server.log 2>&1 &"
echo ""
echo "  开发模式:"
echo "    python3 run.py"
echo ""
echo "  访问: http://服务器IP:80"
echo "  管理员账号由首次启动自动创建"
echo ""
echo "  注意: 腾讯云防火墙需开放80端口"
echo "========================================="
