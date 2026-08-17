from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base
from app.db import models  # noqa: F401
from app.core.redis import close_redis
from app.schemas.config import settings
from app.api import auth, trips, stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：释放 Redis 连接
    await close_redis()


app = FastAPI(
    title="Travel Planner Agent API",
    description="AI-powered travel planning assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(trips.router, prefix=settings.API_V1_STR)
app.include_router(stream.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "Travel Planner Agent API",
        "version": "1.0.0",
        "tech_stack": "FastAPI + LangGraph + PostgreSQL + Redis + ChromaDB",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)