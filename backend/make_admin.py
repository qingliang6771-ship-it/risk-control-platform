"""把指定用户设为管理员（授予全部模块权限）。

用法（在服务器容器内执行，注意用 -w /app/backend 指定工作目录）：
    # 列出所有用户，方便确认
    docker compose exec -w /app/backend risk-platform python make_admin.py --list

    # 按邮箱设为管理员
    docker compose exec -w /app/backend risk-platform python make_admin.py you@company.com

    # 或按 Lark user_id 设为管理员
    docker compose exec -w /app/backend risk-platform python make_admin.py --id ou_xxxxxxxx

    # 不带参数时：把最早登录的第一个用户设为管理员
    docker compose exec -w /app/backend risk-platform python make_admin.py
"""

import asyncio
import json
import sys
from sqlalchemy import text
from app.database import engine
from app.models.user import ALL_MODULES


async def list_users():
    async with engine.begin() as conn:
        rows = await conn.execute(
            text("SELECT id, name, email, is_admin, permitted_modules FROM users ORDER BY created_at ASC")
        )
        users = rows.fetchall()
        if not users:
            print("（数据库中暂无用户，请先用 Lark 登录一次）")
            return
        print(f"{'管理员':<6} {'姓名':<12} {'邮箱':<28} id")
        print("-" * 80)
        for u in users:
            flag = "✔" if u[3] else " "
            print(f"  {flag}    {str(u[1]):<12} {str(u[2]):<28} {u[0]}")


async def set_admin(where_sql: str, params: dict):
    async with engine.begin() as conn:
        # 先查是否存在
        row = await conn.execute(
            text(f"SELECT id, name, email FROM users WHERE {where_sql}"), params
        )
        user = row.fetchone()
        if not user:
            print("❌ 未找到匹配的用户，可先用 --list 查看现有用户。")
            return
        await conn.execute(
            text(
                f"UPDATE users SET is_admin = 1, is_active = 1, permitted_modules = :mods WHERE {where_sql}"
            ),
            {**params, "mods": json.dumps(ALL_MODULES)},
        )
        print(f"✅ 已将用户设为管理员：{user[1]} <{user[2]}> ({user[0]})")
        print("   请重新登录（或刷新页面）即可看到「权限管理」菜单。")


async def main():
    args = sys.argv[1:]

    if args and args[0] == "--list":
        await list_users()
        return

    if args and args[0] == "--id":
        if len(args) < 2:
            print("用法: python make_admin.py --id <lark_user_id>")
            return
        await set_admin("id = :val", {"val": args[1]})
        return

    if args:
        # 按邮箱
        await set_admin("email = :val", {"val": args[0]})
        return

    # 无参数：设最早创建的用户为管理员
    async with engine.begin() as conn:
        first = await conn.execute(text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"))
        row = first.fetchone()
        if not row:
            print("❌ 数据库暂无用户，请先用 Lark 登录一次再运行本脚本。")
            return
    await set_admin("id = :val", {"val": row[0]})


if __name__ == "__main__":
    asyncio.run(main())
