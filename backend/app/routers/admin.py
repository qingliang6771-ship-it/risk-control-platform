"""Admin router - 权限管理（仅管理员可访问）。

功能：
- 列出/搜索使用 Lark 登录过的用户及其模块权限
- 手动添加待授权的 Lark 用户（按 open_id / email 预建账号）
- 编辑某用户的模块权限、启用/停用、管理员标记
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from ..database import get_db
from ..models.user import User, ALL_MODULES, DEFAULT_MODULES
from .auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _serialize(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "avatar_url": u.avatar_url,
        "lark_open_id": u.lark_open_id,
        "department": u.department,
        "is_active": u.is_active,
        "is_admin": u.is_admin,
        "permitted_modules": u.permitted_modules or [],
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


class UpdatePermissionsBody(BaseModel):
    permitted_modules: List[str]
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class AddUserBody(BaseModel):
    name: str
    lark_open_id: str
    email: Optional[str] = None
    permitted_modules: Optional[List[str]] = None
    is_admin: Optional[bool] = False


@router.get("/modules")
async def list_modules(_: User = Depends(require_admin)):
    """返回所有可分配的模块清单（供前端渲染复选框）。"""
    labels = {
        "dashboard": "工作台",
        "ai-report": "AI 数据报告",
        "risk-query": "风控查询",
        "kyc-report": "KYC 报告",
        "permissions": "权限管理",
    }
    return {"modules": [{"key": k, "label": labels.get(k, k)} for k in ALL_MODULES]}


@router.get("/users")
async def list_users(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出所有用户，可按姓名/邮箱模糊搜索。"""
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    result = await db.execute(stmt.order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {"users": [_serialize(u) for u in users]}


@router.post("/users")
async def add_user(
    body: AddUserBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """手动预建一个 Lark 授权用户（用户尚未登录时提前配置权限）。"""
    # 校验模块合法性
    modules = body.permitted_modules if body.permitted_modules is not None else list(DEFAULT_MODULES)
    invalid = [m for m in modules if m not in ALL_MODULES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效模块: {invalid}")

    existing = await db.execute(select(User).where(User.lark_open_id == body.lark_open_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该 Lark OpenID 用户已存在")

    user = User(
        id=body.lark_open_id,
        name=body.name,
        email=body.email,
        lark_open_id=body.lark_open_id,
        is_admin=bool(body.is_admin),
        permitted_modules=modules,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _serialize(user)


@router.put("/users/{user_id}/permissions")
async def update_permissions(
    user_id: str,
    body: UpdatePermissionsBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """更新指定用户的模块权限 / 状态 / 管理员标记。"""
    invalid = [m for m in body.permitted_modules if m not in ALL_MODULES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效模块: {invalid}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.permitted_modules = body.permitted_modules
    if body.is_active is not None:
        # 不允许管理员停用自己
        if user.id == admin.id and body.is_active is False:
            raise HTTPException(status_code=400, detail="不能停用自己的账号")
        user.is_active = body.is_active
    if body.is_admin is not None:
        if user.id == admin.id and body.is_admin is False:
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
        user.is_admin = body.is_admin

    await db.commit()
    await db.refresh(user)
    return _serialize(user)
