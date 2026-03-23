#!/usr/bin/env python3
"""
数据库初始化脚本
用于生产环境部署时初始化数据库

功能:
- 创建数据库(如果不存在)
- 运行数据库迁移
- 创建初始管理员用户
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_database_if_not_exists():
    """创建数据库(如果不存在)"""
    db_url = settings.DATABASE_URL
    db_name = db_url.split("/")[-1].split("?")[0]
    base_url = "/".join(db_url.split("/")[:-1])
    sync_base_url = base_url.replace("+asyncpg", "")

    engine = create_engine(sync_base_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        )
        exists = result.fetchone() is not None

        if not exists:
            print(f"Creating database: {db_name}")
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")

    engine.dispose()


async def run_migrations():
    """运行数据库迁移"""
    import subprocess

    backend_dir = Path(__file__).parent.parent / "backend"
    alembic_ini = backend_dir / "alembic.ini"

    print("Running database migrations...")

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Migration failed: {result.stderr}")
        sys.exit(1)

    print("Migrations completed successfully")


async def create_admin_user():
    """创建初始管理员用户"""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123456")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            text(f"SELECT 1 FROM users WHERE username = '{admin_username}'")
        )
        exists = result.fetchone() is not None

        if exists:
            print(f"Admin user '{admin_username}' already exists")
            return

        hashed_password = pwd_context.hash(admin_password)
        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
        )

        session.add(admin_user)
        await session.commit()
        print(f"Admin user '{admin_username}' created successfully")
        print(f"Email: {admin_email}")
        print("Please change the default password after first login!")

    await engine.dispose()


async def main():
    """主函数"""
    print("=" * 50)
    print("Database Initialization Script")
    print("=" * 50)

    print("\n[1/3] Creating database if not exists...")
    create_database_if_not_exists()

    print("\n[2/3] Running migrations...")
    await run_migrations()

    print("\n[3/3] Creating admin user...")
    await create_admin_user()

    print("\n" + "=" * 50)
    print("Database initialization completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
