"""
FastAPI 应用主入口模块

负责初始化 FastAPI 应用实例、注册中间件、挂载路由，
以及管理应用生命周期（启动时建表、关闭时释放资源）。
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base
from app.db import models  # noqa: F401 — 导入以确保 ORM 模型被注册
from app.core.redis import close_redis
from app.schemas.config import settings
from app.api import auth, trips, stream, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时异步创建所有数据库表（基于 SQLAlchemy ORM 模型）；
    关闭时释放 Redis 连接池。

    Args:
        app: FastAPI 应用实例

    Yields:
        控制权交给应用运行阶段，启动与关闭逻辑分别在 yield 前后执行
    """
    # 启动时：遍历所有 Base 子类，在数据库中创建对应的表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：释放 Redis 连接
    await close_redis()


# 创建 FastAPI 应用实例，配置标题、描述、版本及生命周期管理器
app = FastAPI(
    title="Travel Planner Agent API",
    description="AI-powered travel planning assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册 CORS 中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 允许的来源域名列表
    allow_credentials=True,               # 允许携带 Cookie 等凭证
    allow_methods=["*"],                  # 允许所有 HTTP 方法
    allow_headers=["*"],                  # 允许所有请求头
)

# 注册各功能路由模块，统一添加 API 版本前缀
app.include_router(auth.router, prefix=settings.API_V1_STR)   # 认证相关接口
app.include_router(trips.router, prefix=settings.API_V1_STR)  # 行程管理接口
app.include_router(stream.router, prefix=settings.API_V1_STR) # 流式响应接口
app.include_router(profile.router, prefix=settings.API_V1_STR)  # 用户画像接口


@app.get("/")
def root():
    """根路由，返回 API 基本信息与技术栈说明"""
    return {
        "message": "Travel Planner Agent API",
        "version": "1.0.0",
        "tech_stack": "FastAPI + LangGraph + PostgreSQL + Redis + ChromaDB",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """健康检查接口，用于监控与负载均衡存活探测"""
    return {"status": "healthy"}


# 直接运行时启动 Uvicorn 开发服务器（支持热重载）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)