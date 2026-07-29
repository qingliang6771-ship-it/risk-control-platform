"""一次性迁移脚本：为已存在的 users 表补充权限相关列。

用途：如果你在加入「权限管理」功能前已经有旧数据库（users 表已建），
运行本脚本即可安全地补上 is_admin / permitted_modules 两列，
并把已有用户默认授予基础模块权限（第一个用户设为管理员）。

用法：
    cd backend
    python migrate_add_permissions.py

新库（首次部署）无需运行本脚本，应用启动时会自动建表。
"""
import asyncio
import json
from sqlalchemy import text
from app.database import engine
from app.config import settings
from app.models.user import DEFAULT_MODULES, ALL_MODULES


async def column_exists(conn, table: str, column: str) -> bool:

    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    cols = [row[1] for row in result.fetchall()]
    return column in cols


async def main():
    # 本迁移脚本使用 SQLite 语法（PRAGMA），仅对 SQLite 生效
    if "sqlite" not in settings.DATABASE_URL:
        print("非 SQLite 数据库，跳过本脚本（请使用 Alembic 等工具管理迁移）。")
        return

    async with engine.begin() as conn:

        # 检查表是否存在
        tables = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        )
        if not tables.fetchall():
            print("users 表不存在，应用首次启动会自动创建，无需迁移。")
            return

        # 补 is_admin 列
        if not await column_exists(conn, "users", "is_admin"):
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            print("已添加列: is_admin")
        else:
            print("列 is_admin 已存在，跳过")

        # 补 permitted_modules 列
        if not await column_exists(conn, "users", "permitted_modules"):
            await conn.execute(text("ALTER TABLE users ADD COLUMN permitted_modules JSON"))
            print("已添加列: permitted_modules")
        else:
            print("列 permitted_modules 已存在，跳过")

        # 为空权限的用户填充默认模块
        rows = await conn.execute(
            text("SELECT id FROM users WHERE permitted_modules IS NULL OR permitted_modules = ''")
        )
        ids = [r[0] for r in rows.fetchall()]
        for uid in ids:
            await conn.execute(
                text("UPDATE users SET permitted_modules = :mods WHERE id = :id"),
                {"mods": json.dumps(DEFAULT_MODULES), "id": uid},
            )
        if ids:
            print(f"已为 {len(ids)} 个用户设置默认模块权限")

        # 若没有任何管理员，把最早创建的用户设为管理员并授予全部权限
        admins = await conn.execute(text("SELECT COUNT(*) FROM users WHERE is_admin = 1"))
        if (admins.scalar() or 0) == 0:
            first = await conn.execute(
                text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
            )
            row = first.fetchone()
            if row:
                await conn.execute(
                    text("UPDATE users SET is_admin = 1, permitted_modules = :mods WHERE id = :id"),
                    {"mods": json.dumps(ALL_MODULES), "id": row[0]},
                )
                print(f"已将用户 {row[0]} 设为管理员")

    print("迁移完成 ✅")


if __name__ == "__main__":
    asyncio.run(main())
