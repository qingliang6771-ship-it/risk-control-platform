"""迁移脚本：创建/升级封禁记录表 ban_records。

用法（在 backend 目录下）：
    python migrate_add_bans.py

对已部署环境安全：
- 表不存在时创建（create_all 幂等）
- 表已存在但缺少新列（cleared）时，自动 ALTER TABLE 补列
"""
import asyncio

from sqlalchemy import text

from app.database import engine, Base
# 确保模型被导入并注册到 Base.metadata
from app.models.ban import BanRecord  # noqa: F401


async def _column_exists(conn, table: str, column: str) -> bool:
    """兼容 SQLite / Postgres 检查列是否存在。"""
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
        return any(r[1] == column for r in rows)
    # postgres / 其他
    res = await conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return res.first() is not None


async def migrate():
    async with engine.begin() as conn:
        # 1) 创建表（若不存在）
        await conn.run_sync(Base.metadata.create_all)

        # 2) 为已有表补 cleared 列
        if not await _column_exists(conn, "ban_records", "cleared"):
            dialect = conn.engine.dialect.name
            if dialect == "sqlite":
                await conn.execute(text(
                    "ALTER TABLE ban_records ADD COLUMN cleared BOOLEAN NOT NULL DEFAULT 0"
                ))
            else:
                await conn.execute(text(
                    "ALTER TABLE ban_records ADD COLUMN cleared BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            print("✅ 已为 ban_records 添加 cleared 列")
        else:
            print("ℹ️ cleared 列已存在，跳过")

    print("✅ ban_records 表已创建/升级完成")


if __name__ == "__main__":
    asyncio.run(migrate())
