"""迁移脚本：创建封禁记录表 ban_records。

用法（在 backend 目录下）：
    python migrate_add_bans.py

对已部署环境安全：表已存在时不会重复创建（create_all 幂等）。
"""
import asyncio

from app.database import engine, Base
# 确保模型被导入并注册到 Base.metadata
from app.models.ban import BanRecord  # noqa: F401


async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ ban_records 表已创建/确认存在")


if __name__ == "__main__":
    asyncio.run(migrate())
