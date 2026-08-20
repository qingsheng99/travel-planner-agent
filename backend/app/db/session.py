"""
数据库会话管理模块

创建异步 SQLAlchemy 引擎与会话工厂，并提供 FastAPI 依赖注入
函数 get_db() 供路由处理器获取数据库会话。
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.schemas.config import settings

# 创建异步数据库引擎，配置连接池参数
# pool_size: 连接池大小；max_overflow: 超出池大小的最大连接数
# pool_pre_ping: 每次借用连接前发送 ping 检测连接有效性
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,           # 不打印 SQL 语句（生产环境关闭）
    pool_size=20,         # 连接池保持 20 个连接
    max_overflow=10,      # 最多额外创建 10 个连接应对突发流量
    pool_pre_ping=True,   # 连接复用前检查是否存活
)

# 异步会话工厂，每次调用 get_db() 时创建一个新的 AsyncSession 实例
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不自动过期，避免后续访问懒加载属性时报错
    autocommit=False,        # 手动管理事务提交
    autoflush=False,         # 手动管理 flush，避免查询前自动 flush 导致意外写操作
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有数据模型应继承此类"""
    pass


async def get_db():
    """
    FastAPI 依赖注入函数，提供数据库会话

    每个请求通过此函数获取一个 AsyncSession 实例，
    请求结束后自动关闭会话释放回连接池。

    Yields:
        AsyncSession: 数据库会话对象
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()