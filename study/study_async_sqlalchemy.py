"""
================================================================================
           异步 SQLAlchemy 学习指南 —— 基于 Travel Planner 项目实战
================================================================================

本文件从项目中的实际代码出发，逐步讲解异步 SQLAlchemy 的核心概念。
建议按顺序运行每个 Part，配合注释理解。

环境准备：
    pip install sqlalchemy[asyncio] asyncpg

运行方式：
    python study_async_sqlalchemy.py

注意：依赖本地 PostgreSQL，请在运行前确保 PostgreSQL 已启动。
      默认连接 postgresql://travel:travel123@localhost:5432/travel_planner
      可通过环境变量覆盖：set PG_DSN=postgresql+asyncpg://user:pass@host/db
"""

import asyncio
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any


# ============================================================================
#   Part 0: 前置知识 —— 为什么用异步？
# ============================================================================
#
# 传统同步写法：一个请求 → 一个线程 → 线程在等数据库时被"卡住"
# 异步写法：   一个请求 → 一个协程 → 协程在等数据库时"让出"CPU，去处理别的请求
#
# 项目用 asyncpg 驱动 + async SQLAlchemy，后端在高并发下能支撑更多连接。
# 简单说：异步 = 不浪费 CPU 等待 I/O。


# ============================================================================
#   Part 1: 创建引擎和会话（对应项目 db/session.py）
# ============================================================================

# ── 1.1 引擎（Engine） ──────────────────────────────────────────────────────
# 引擎是数据库连接的"工厂"，负责管理连接池。
# 异步引擎用 create_async_engine，同步用 create_engine，接口几乎一样。

from sqlalchemy.ext.asyncio import (
    create_async_engine,       # 创建异步引擎
    AsyncSession,              # 异步会话的类
    async_sessionmaker,        # 会话工厂
)

# 这是项目中的拼接方式（见 schemas/config.py）
# 关键区别：协议从 postgresql+asyncpg:// 而不是 postgresql://
DATABASE_URL = os.getenv("PG_DSN", "postgresql+asyncpg://travel:travel123@localhost:5432/travel_planner")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,           # True 会打印所有 SQL 语句，学习时建议打开
    pool_size=5,          # 连接池大小
    max_overflow=10,      # 超过 pool_size 时最多额外创建多少连接
    pool_pre_ping=True,   # 每次从池取出连接前先"ping"一下，防止连接断开
)

# ── 1.2 会话工厂（Session Maker） ────────────────────────────────────────────
# 项目中的写法（见 db/session.py）：
#   AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, ...)
#
# Session = 会话 = 一次"与数据库的对话"。你可以在一个会话里执行多个查询，
# 最后 commit 或 rollback。类比：打开一个文本编辑器窗口，做多个修改，最后保存或放弃。

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,           # 使用异步会话类
    expire_on_commit=False,        # commit 后不过期对象（后面会解释）
    autocommit=False,              # 不自动提交，手动控制事务
    autoflush=False,               # 不自动刷新，手动控制
)


# ── 1.3 声明式基类（Base） ──────────────────────────────────────────────────
# 所有模型类都继承自 Base，SQLAlchemy 通过它知道你有哪些表。

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


# ── 1.4 依赖注入中的 get_db（项目 db/session.py） ────────────────────────────
# 在 FastAPI 中，每个请求都通过这个函数获取一个"干净"的会话。
# 请求结束后自动关闭，释放连接回连接池。

async def get_db():
    """模拟 FastAPI 的依赖注入 —— 每次请求一个会话，用完自动关闭"""
    async with AsyncSessionLocal() as session:
        # 项目中的写法：
        #   try:
        #       yield session     # FastAPI 注入给路由
        #   finally:
        #       await session.close()
        #
        # 这里我们直接返回，调用方手动管理
        return session


# ============================================================================
#   Part 2: 定义模型（对应项目 db/models.py）
# ============================================================================

# ── 2.1 字段类型导入 ────────────────────────────────────────────────────────

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Float,
    ForeignKey, UniqueConstraint, Index,
    JSON,                           # PostgreSQL 的 JSON 字段
)
from sqlalchemy.orm import (
    Mapped,                         # 类型注解：标记一个字段"映射到数据库列"
    mapped_column,                  # 定义列的具体属性（类型、约束等）
    relationship,                   # 定义表之间的关系
)
from sqlalchemy.sql import func    # 用于 server_default=func.now() 等


# ── 2.2 定义第一个模型 ──────────────────────────────────────────────────────
#
# 关键语法：
#   id: Mapped[int] = mapped_column(Integer, primary_key=True)
#            ↑                   ↑
#        类型注解         列定义（类型、约束等）
#
# 这是 SQLAlchemy 2.0 的"声明式映射"写法，对比旧写法：
#   旧：id = Column(Integer, primary_key=True)
#   新：id: Mapped[int] = mapped_column(Integer, primary_key=True)
# 新写法更好的类型提示，IDE 能帮你自动补全。

class User(Base):
    """用户表 —— 对应项目中的 User 模型"""
    __tablename__ = "study_users"  # 表名，加 study_ 前缀避免和项目冲突

    # ── 基本字段 ────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    #    ↑ 类型注解              ↑ 列定义
    # Mapped[int] 表示这个字段是 int 类型，对应数据库列
    # mapped_column(...) 指定数据库列的具体属性

    email: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    # unique=True → 数据库 UNIQUE 约束
    # index=True  → 自动创建索引，加快按 email 查询速度
    # nullable=False → NOT NULL

    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── 时间字段 ────────────────────────────────────────────────────────
    # server_default = 数据库默认值（在 SQL 层面设置）
    # onupdate      = 更新时自动设置

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),     # 带时区的时间类型
        server_default=func.now(),   # 数据库自动填入当前时间
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),         # 每次更新行时自动更新时间
        nullable=True,
    )

    # ── 关系（Relationship） ─────────────────────────────────────────────
    # relationship 不会在数据库层面创建列，它只是一个"Python 层面的关联"，
    # 让你能通过 user.trips 直接访问关联的行程对象。
    #
    # back_populates：告诉 SQLAlchemy，这个关系在对方模型里叫啥名字。
    # 必须"双向对应"，否则 SQLAlchemy 搞不清谁关联谁。

    trips: Mapped[List["Trip"]] = relationship(back_populates="owner")

    # ── 如何记忆 mapped_column 参数 ─────────────────────────────────────
    # 常用参数一览：
    #
    # primary_key=True    → 主键
    # index=True          → 创建索引
    # unique=True         → 唯一约束
    # nullable=False      → 不能为空
    # default=xxx         → Python 层面的默认值
    # server_default=xxx  → 数据库层面的默认值
    # onupdate=xxx        → 更新时自动设置
    # comment="xxx"       → 字段注释


class Trip(Base):
    """行程表 —— 对应项目中的 Trip 模型"""
    __tablename__ = "study_trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── 外键 ────────────────────────────────────────────────────────────
    # ForeignKey("study_users.id") 表示这个字段引用 study_users 表的 id 列
    # 数据库层面：自动创建外键约束，保证 user_id 一定对应一个存在的用户
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("study_users.id"))

    title: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)

    # ── Optional 和 nullable ────────────────────────────────────────────
    # Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Optional[X] 等价于 X | None，表示这个字段"可以为空"
    # nullable=True 表示数据库列允许 NULL
    # 两者要一致：类型注解写 Optional，列定义也要 nullable=True
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── JSON 字段 ───────────────────────────────────────────────────────
    # PostgreSQL 支持 JSON 类型，SQLAlchemy 用 dialect-specific 的 JSON 类型
    # 项目中的导入：from sqlalchemy.dialects.postgresql import JSON
    # 存 Python 的 dict/list 会自动序列化/反序列化
    budget: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    itinerary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    travelers: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="planning")

    # ── 时间戳 ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # ── 反向关系 ────────────────────────────────────────────────────────
    # User.trips 和 Trip.owner 是双向的
    # back_populates="trips" 告诉 SQLAlchemy：
    #   "对方（User.trips）里，这个关系叫 trips"
    owner: Mapped["User"] = relationship(back_populates="trips")


# ============================================================================
#   Part 3: CRUD 操作 —— 最常用的数据库操作
# ============================================================================

# ── 3.1 导入查询工具 ────────────────────────────────────────────────────────

from sqlalchemy import select, delete, update, func as sql_func
# select  → 查询（SELECT）
# delete  → 删除（DELETE）
# update  → 更新（UPDATE）
# func    → 聚合函数（count, sum, now 等）


# ── 3.2 CREATE —— 创建 ──────────────────────────────────────────────────────

async def demo_create(session: AsyncSession) -> User:
    """
    创建用户 —— 对应项目 api/auth.py 的 register 接口

    流程：
        1. 创建 Python 对象
        2. session.add() 加入会话（可以理解为"标记为待插入"）
        3. session.commit() 提交事务（真正写入数据库）
        4. session.refresh() 从数据库刷新对象（获取数据库生成的 id 和 created_at）
    """
    print("\n" + "=" * 60)
    print("  [CREATE] 创建新用户")
    print("=" * 60)

    # Step 1: 创建对象 —— 就像实例化普通 Python 类一样
    user = User(
        email="alice@example.com",
        username="alice",
        hashed_password="hashed_pwd_123",  # 实际项目中用 bcrypt 哈希
        is_active=True,
    )
    print(f"  创建对象: username={user.username}, id={user.id}")
    print(f"    → 此时 id 为 None，因为还没写入数据库")

    # Step 2: 加入会话
    session.add(user)
    print(f"    → add() 后，对象被标记为 '待插入'")

    # Step 3: 提交事务
    await session.commit()
    print(f"    → commit() 后，数据已写入数据库")

    # Step 4: 从数据库刷新
    await session.refresh(user)
    print(f"    → refresh() 后，id={user.id}")
    print(f"    → created_at={user.created_at}（数据库自动生成的）")

    return user


async def demo_create_trip(session: AsyncSession, user_id: int) -> Trip:
    """
    创建行程 —— 对应项目 services/itinerary.py 的 create_trip

    注意：JSON 字段可以直接传 Python dict/list
    """
    print("\n" + "=" * 60)
    print("  [CREATE] 创建行程")
    print("=" * 60)

    trip = Trip(
        user_id=user_id,
        title="北京之旅",
        destination="北京",
        start_date=datetime(2026, 9, 1),
        end_date=datetime(2026, 9, 3),
        budget={"min": 3000, "max": 8000},
        travelers=2,
        status="planning",
        itinerary={},           # 空字典，等 AI 生成后填充
    )

    session.add(trip)
    await session.commit()
    await session.refresh(trip)

    print(f"  创建行程: {trip.title} → {trip.destination}")
    print(f"  id={trip.id}, 预算={trip.budget}")

    return trip


# ── 3.3 READ —— 查询 ────────────────────────────────────────────────────────

async def demo_read(session: AsyncSession):
    """
    查询 —— 对应项目 services/auth.py 和 services/itinerary.py

    核心模式：
        result = await session.execute(select(Model).where(...))
        result.scalar_one_or_none()   # 取一个结果，没有则返回 None
        result.scalars().all()        # 取所有结果
    """
    print("\n" + "=" * 60)
    print("  [READ] 查询演示")
    print("=" * 60)

    # ── 查询单个用户（按 email） ────────────────────────────────────────
    # 这是项目中最常见的模式：先用 select() 构建查询，再用 execute() 执行
    # select(User)  ≈  SELECT * FROM study_users
    # .where(...)    ≈  WHERE ...

    stmt = select(User).where(User.email == "alice@example.com")
    #   ↑ 构建查询（还没执行）

    result = await session.execute(stmt)
    #   ↑ 执行查询

    user = result.scalar_one_or_none()
    #   ↑ 取结果：scalar_one_or_none() 返回一个对象或 None
    #   其他变体：
    #     scalar_one()     → 必须有一个结果，否则抛异常
    #     scalar()         → 取第一个结果，没有则返回 None
    #     scalars().all()  → 取所有结果，返回列表

    print(f"  按 email 查询: {user.username if user else '未找到'}")

    # ── 查询所有行程（按用户 ID） ────────────────────────────────────────
    # 带排序的查询

    stmt = (
        select(Trip)
        .where(Trip.user_id == user.id)
        .order_by(Trip.created_at.desc())  # 按创建时间倒序
    )
    result = await session.execute(stmt)
    trips = result.scalars().all()  # 返回 Trip 对象列表

    print(f"  查询用户的所有行程: 共 {len(trips)} 条")

    # ── 查询单条 + 字段筛选 ──────────────────────────────────────────────
    # 如果想只查某几个字段，不查整行：

    stmt = select(Trip.id, Trip.title, Trip.destination).where(Trip.id == trips[0].id)
    result = await session.execute(stmt)
    row = result.one()  # 返回一个元组 (id, title, destination)
    print(f"  字段筛选: id={row.id}, title={row.title}, dest={row.destination}")

    # ── 聚合查询 ──────────────────────────────────────────────────────────
    # 统计某个用户的行程数量

    stmt = select(sql_func.count(Trip.id)).where(Trip.user_id == user.id)
    result = await session.execute(stmt)
    count = result.scalar()  # 取单个标量值
    print(f"  聚合查询: 该用户共有 {count} 条行程")

    return user, trips


# ── 3.4 UPDATE —— 更新 ──────────────────────────────────────────────────────

async def demo_update(session: AsyncSession, trip: Trip):
    """
    更新 —— 对应项目 services/itinerary.py 的 update_trip_itinerary

    操作方式：直接修改对象的属性，然后 commit
    """
    print("\n" + "=" * 60)
    print("  [UPDATE] 更新行程")
    print("=" * 60)

    # 方式一：直接修改 + commit（推荐，代码清晰）
    trip.status = "planned"
    trip.itinerary = {
        "content": "Day 1: 故宫 → 天安门\nDay 2: 长城\nDay 3: 颐和园",
    }
    # SQLAlchemy 会自动追踪哪些字段变了（称为"脏追踪"）
    # 你不需要额外调用 session.update() 或 session.add()
    # 直接 commit 即可

    await session.commit()
    # 注意：commit 后，session.refresh(trip) 可以获取 updated_at 的新值
    await session.refresh(trip)

    print(f"  状态已更新为: {trip.status}")
    print(f"  itinerary 已填充")
    print(f"  updated_at = {trip.updated_at}")


# ── 3.5 DELETE —— 删除 ──────────────────────────────────────────────────────

async def demo_delete(session: AsyncSession, user: User):
    """
    删除 —— 调用 session.delete() + commit
    """
    print("\n" + "=" * 60)
    print("  [DELETE] 删除演示")
    print("=" * 60)

    # 先查一下该用户有没有行程，有的话先删行程（避免外键约束冲突）
    stmt = select(Trip).where(Trip.user_id == user.id)
    result = await session.execute(stmt)
    trips = result.scalars().all()

    for trip in trips:
        await session.delete(trip)
        print(f"  删除行程: {trip.title}")

    # 再删除用户
    await session.delete(user)
    print(f"  删除用户: {user.username}")

    await session.commit()
    print("  commit 后，删除永久生效")


# ============================================================================
#   Part 4: 关系查询 —— 关联多个表
# ============================================================================

async def demo_relationship(session: AsyncSession):
    """
    SQLAlchemy 关系查询 —— 懒加载 vs 预加载

    关键概念：
        - 懒加载（Lazy Loading）：用 user.trips 时，SQLAlchemy 自动发 SQL 查
        - 预加载（Eager Loading）：用 selectinload() 或 joinedload() 一次性查好
    """
    print("\n" + "=" * 60)
    print("  [RELATIONSHIP] 关系查询")
    print("=" * 60)

    # ── 先创建一些数据 ──────────────────────────────────────────────────
    user = User(
        email="bob@example.com",
        username="bob",
        hashed_password="hashed_pwd_456",
    )
    trip1 = Trip(user_id=0, title="上海之旅", destination="上海")  # user_id 临时
    trip2 = Trip(user_id=0, title="成都之旅", destination="成都")

    session.add_all([user, trip1, trip2])
    await session.flush()  # flush 不提交，但会把数据发到数据库，获取 id
    # flush vs commit：
    #   flush()  → 发送 SQL 到数据库，但事务未提交（可回滚）
    #   commit() → 提交事务（不可回滚）

    # 修正 user_id
    trip1.user_id = user.id
    trip2.user_id = user.id
    await session.commit()

    # ── 懒加载示例 ──────────────────────────────────────────────────────
    # 从数据库重新查用户（清掉 session 缓存）
    session.expire_all()  # 让所有对象"过期"，下次访问时会重新从数据库加载

    stmt = select(User).where(User.email == "bob@example.com")
    result = await session.execute(stmt)
    user = result.scalar_one()

    # 第一次访问 user.trips 时，SQLAlchemy 会自动发一条 SQL 查询
    print(f"  懒加载: 访问 user.trips 时自动查询")
    trips = user.trips  # 这行会触发新的 SQL 查询
    print(f"  user.trips 共有 {len(trips)} 条行程")

    # ── 预加载示例 ──────────────────────────────────────────────────────
    # 用 selectinload() 一次性查好关联数据，避免 N+1 问题
    from sqlalchemy.orm import selectinload

    stmt = (
        select(User)
        .where(User.email == "bob@example.com")
        .options(selectinload(User.trips))  # 一次性把 trips 也查出来
    )
    result = await session.execute(stmt)
    user = result.scalar_one()

    print(f"  预加载: 只发一次 SQL 就查出了用户和行程")
    print(f"  user.trips[0].destination = {user.trips[0].destination}")

    # 清理
    for trip in user.trips:
        await session.delete(trip)
    await session.delete(user)
    await session.commit()


# ============================================================================
#   Part 5: 事务管理 —— 要么全成功，要么全失败
# ============================================================================

async def demo_transaction(session: AsyncSession):
    """
    事务（Transaction）

    核心概念：一组操作要么全部成功（commit），要么全部回滚（rollback）。
    确保数据一致性。

    项目中的例子：创建行程时，同时创建 Trip 和 Conversation。
    如果 Conversation 创建失败，Trip 也不应该被保存。
    """
    print("\n" + "=" * 60)
    print("  [TRANSACTION] 事务管理")
    print("=" * 60)

    # 先创建用户
    user = User(email="carol@test.com", username="carol", hashed_password="xxx")
    session.add(user)
    await session.flush()

    # ── 模拟成功事务 ────────────────────────────────────────────────────
    try:
        trip1 = Trip(user_id=user.id, title="三亚之旅", destination="三亚")
        trip2 = Trip(user_id=user.id, title="厦门之旅", destination="厦门")
        session.add_all([trip1, trip2])

        await session.commit()  # 两个行程一起写入
        print("  事务成功: 两条行程同时写入")
    except Exception as e:
        await session.rollback()  # 异常时回滚
        print(f"  事务回滚: {e}")

    # ── 模拟失败事务 ────────────────────────────────────────────────────
    try:
        # 故意传入一个不存在的 user_id，触发外键错误
        bad_trip = Trip(user_id=99999, title="无效行程", destination="火星")
        session.add(bad_trip)
        await session.commit()
        print("  这行不会执行，因为上面会报错")
    except Exception as e:
        await session.rollback()
        print(f"  事务回滚(预期): 外键约束失败 → {type(e).__name__}")

    # 清理
    stmt = select(Trip).where(Trip.user_id == user.id)
    result = await session.execute(stmt)
    for t in result.scalars().all():
        await session.delete(t)
    await session.delete(user)
    await session.commit()


# ============================================================================
#   Part 6: 深入理解 expire_on_commit
# ============================================================================

async def demo_expire_on_commit():
    """
    expire_on_commit 的作用

    项目里设置 expire_on_commit=False，这是为什么？

    默认 expire_on_commit=True：
        commit() 后，所有对象的属性都被"标记为过期"。
        下次访问任何属性时，SQLAlchemy 都会自动发一条 SQL 重新加载。
        这在异步环境可能有问题（需要在 await 中访问）。

    expire_on_commit=False：
        commit() 后，对象保持原样，你可以直接访问属性。
        但注意：如果数据库有其他事务修改了数据，你拿到的可能是旧值。
    """
    print("\n" + "=" * 60)
    print("  [EXPIRE_ON_COMMIT] 深入理解")
    print("=" * 60)

    # 用 expire_on_commit=True 的会话
    session_expire = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )()

    # 用 expire_on_commit=False 的会话（项目中的设置）
    session_no_expire = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )()

    try:
        # 创建测试用户
        user = User(email="expire@test.com", username="expire_test", hashed_password="x")
        session_expire.add(user)
        await session_expire.commit()
        user_id = user.id

        # 测试 expire_on_commit=True
        print(f"  expire_on_commit=True:")
        print(f"    commit 后 id={user.id}，但...")
        print(f"    如果在这里访问 user.username，会自动触发 SELECT 重新加载")
        print(f"    这在异步中需要小心，可能需要在 async 函数中访问")

        # 测试 expire_on_commit=False
        user2 = await session_no_expire.get(User, user_id)
        print(f"  expire_on_commit=False:")
        print(f"    get 后 username={user2.username}")
        # commit 后对象不会过期，属性可以直接访问
        await session_no_expire.commit()
        print(f"    commit 后 username={user2.username}（仍然可用，不会触发额外查询）")

        # 清理
        await session_expire.delete(user)
        await session_expire.commit()

    finally:
        await session_expire.close()
        await session_no_expire.close()


# ============================================================================
#   Part 7: 项目实战对照 —— 对应项目中的实际代码
# ============================================================================

async def demo_project_patterns(session: AsyncSession):
    """
    对照项目中的实际代码模式

    模式一：services/auth.py —— 按 email 查用户
    模式二：services/itinerary.py —— 创建行程同时创建对话
    模式三：api/trips.py —— 查询并校验权限
    """
    print("\n" + "=" * 60)
    print("  [PROJECT PATTERNS] 项目实战模式对照")
    print("=" * 60)

    # 创建测试数据
    user = User(email="pattern@test.com", username="pattern_test", hashed_password="x")
    session.add(user)
    await session.flush()

    # ── 模式一：按 email 查用户（对应 services/auth.py） ────────────────
    # 项目中原代码：
    #   async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    #       result = await db.execute(select(User).where(User.email == email))
    #       return result.scalar_one_or_none()

    stmt = select(User).where(User.email == "pattern@test.com")
    result = await session.execute(stmt)
    found_user = result.scalar_one_or_none()
    print(f"  模式一: 按 email 查用户 → {found_user.username}")

    # ── 模式二：创建行程 + 会话（对应 services/itinerary.py） ────────────
    # 项目中原代码：
    #   trip = Trip(...)
    #   db.add(trip)
    #   await db.commit()
    #   conversation = Conversation(trip_id=trip.id, messages=[])
    #   db.add(conversation)
    #   await db.commit()
    # 注意：这里在 commit 后刷新 trip 来获取 trip.id

    trip = Trip(user_id=user.id, title="模式测试", destination="测试地")
    session.add(trip)
    await session.commit()
    await session.refresh(trip)
    print(f"  模式二: 创建行程 id={trip.id}")

    # ── 模式三：查询 + 权限校验（对应 api/trips.py） ─────────────────────
    # 项目中原代码：
    #   trip = await get_trip(db, trip_id)
    #   if not trip:
    #       raise HTTPException(status_code=404)
    #   if trip.user_id != current_user.id:
    #       raise HTTPException(status_code=403)

    stmt = select(Trip).where(Trip.id == trip.id)
    result = await session.execute(stmt)
    found_trip = result.scalar_one_or_none()

    if found_trip is None:
        print(f"  模式三: 行程不存在")
    elif found_trip.user_id != user.id:
        print(f"  模式三: 无权限访问")
    else:
        print(f"  模式三: 权限校验通过，可以访问 {found_trip.title}")

    # 清理
    await session.delete(trip)
    await session.delete(user)
    await session.commit()


# ============================================================================
#   Part 8: 常见陷阱与注意事项
# ============================================================================

def common_pitfalls():
    """
    常见陷阱和注意事项 —— 建议记忆

    1.  SELECT * FROM study_users WHERE email = ? 和 WHERE email == ?
        SQLAlchemy 中 == 是 Python 的 ==，不是 SQL 的 =
        select(User).where(User.email == "xxx")  ✅
        select(User).where(User.email = "xxx")   ❌ SyntaxError

    2.  Add 后忘记 commit
        user = User(...)
        session.add(user)
        # 忘记 await session.commit() → 数据不会写入数据库

    3.  await 每个异步操作
        session.add(user)     # 同步，不需要 await
        await session.commit()  # 异步，必须 await

    4.  session 不是线程安全的
        每个请求/协程用自己独立的 session，不要共享

    5.  JSON 字段的默认值
        budget: Mapped[Dict] = mapped_column(JSON, default=dict)
        # 注意：default=dict 而不是 default={}
        # default={} 会导致所有实例共享同一个 dict，是 Python 的经典陷阱

    6.  SELECT N+1 问题
        for user in users:       # 1 条 SQL 查询所有用户
            print(user.trips)    # N 条 SQL：每个用户各查一次
        # 解决方案：用 selectinload() 或 joinedload() 预加载
    """
    print("\n" + "=" * 60)
    print("  [COMMON PITFALLS] 常见陷阱")
    print("=" * 60)

    pitfalls = [
        ("用 == 而不是 =", "select(User).where(User.email == 'x')  # ✅ 正确"),
        ("忘记 await", "await session.commit()  # 必须 await"),
        ("JSON 默认值", "default=dict 而不是 default={}"),
        ("N+1 查询", "用 selectinload() 预加载关联数据"),
        ("会话管理", "每个请求/协程用独立 session"),
    ]
    for title, desc in pitfalls:
        print(f"  ⚠ {title}: {desc}")


# ============================================================================
#   Part 9: 主函数 —— 按顺序运行所有演示
# ============================================================================

async def main():
    """主函数：按顺序执行所有学习示例"""
    print("=" * 70)
    print("  异步 SQLAlchemy 学习之旅")
    print("  基于 Travel Planner 项目实战代码")
    print("=" * 70)

    print("\n📌 连接数据库:", DATABASE_URL)

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ 表已创建")

    # 获取会话
    session = await get_db()

    try:
        # ── Part 3: CRUD ────────────────────────────────────────────────
        user = await demo_create(session)
        trip = await demo_create_trip(session, user.id)
        await demo_read(session)
        await demo_update(session, trip)
        await demo_delete(session, user)

        # ── Part 4: 关系 ────────────────────────────────────────────────
        await demo_relationship(session)

        # ── Part 5: 事务 ────────────────────────────────────────────────
        await demo_transaction(session)

        # ── Part 6: expire_on_commit ────────────────────────────────────
        await demo_expire_on_commit()

        # ── Part 7: 项目模式 ────────────────────────────────────────────
        await demo_project_patterns(session)

        # ── Part 8: 常见陷阱 ────────────────────────────────────────────
        common_pitfalls()

        print("\n" + "=" * 70)
        print("  🎉 所有演示完成！")
        print("=" * 70)

    finally:
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())