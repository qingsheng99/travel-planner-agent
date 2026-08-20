"""
数据库初始数据填充脚本

创建数据库表结构并插入演示账号，方便开发环境快速启动和测试。
运行前确保数据库连接配置正确（由 settings.DATABASE_URL_SYNC 指定）。
"""

import sys
import os
# 将项目根目录加入 Python 模块搜索路径，确保可以直接导入 backend 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import Base, User
from app.services.auth import get_password_hash
from app.schemas.config import settings

# 创建同步数据库引擎
engine = create_engine(settings.DATABASE_URL_SYNC)


def seed_database():
    """初始化数据库：创建表结构并插入演示账号

    自动创建所有继承自 Base 的数据表（如 User 表）。
    检查是否已存在演示账号，若不存在则创建。
    演示账号信息：demo@example.com / demo123

    Returns:
        None
    """
    Base.metadata.create_all(bind=engine)                             # 创建所有表（如不存在）

    with Session(engine) as db:
        # 查询演示账号是否已存在
        user = db.execute(select(User).where(User.email == "demo@example.com")).scalar_one_or_none()
        if not user:
            # 不存在则创建演示账号
            user = User(
                email="demo@example.com",
                username="demo",
                hashed_password=get_password_hash("demo123"),          # 密码加密存储
            )
            db.add(user)                                              # 添加到 session
            db.commit()                                               # 提交事务
            print("[OK] 演示账号: demo@example.com / demo123")
        else:
            print("[OK] 演示账号已存在")

        print("[OK] 数据库初始化完成!")


if __name__ == "__main__":
    seed_database()