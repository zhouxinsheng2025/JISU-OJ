FROM python:3.12-slim

WORKDIR /app

# 安装编译工具(gcc/g++/javac供判题使用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ default-jdk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p runs data/testcases

EXPOSE 8000

# 生产模式: gunicorn + uvicorn workers (4个进程)
# 开发模式可覆盖: docker run ... uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
CMD gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile -
