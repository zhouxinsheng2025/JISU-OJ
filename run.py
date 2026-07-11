import uvicorn

if __name__ == "__main__":
    # 开发模式: 单进程 + 热重载
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
