import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import Base, User
from app.services.auth import get_password_hash
from app.schemas.config import settings

engine = create_engine(settings.DATABASE_URL_SYNC)


def seed_database():
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        user = db.execute(select(User).where(User.email == "demo@example.com")).scalar_one_or_none()
        if not user:
            user = User(
                email="demo@example.com",
                username="demo",
                hashed_password=get_password_hash("demo123"),
            )
            db.add(user)
            db.commit()
            print("[OK] 演示账号: demo@example.com / demo123")
        else:
            print("[OK] 演示账号已存在")

        print("[OK] 数据库初始化完成!")


if __name__ == "__main__":
    seed_database()