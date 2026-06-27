from fastapi import FastAPI
from app.config import settings

app = FastAPI(title="程序设计裁判系统")


@app.on_event("startup")
async def startup():
    from app.database import init_db
    await init_db()


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/team/login")
