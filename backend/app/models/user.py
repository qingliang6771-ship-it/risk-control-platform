"""User model."""
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from ..database import Base

# 所有可分配的模块 key（与前端菜单 key 对应）
ALL_MODULES = ["dashboard", "ai-report", "risk-query", "kyc-report", "chargeback-report", "permissions"]
# 新用户默认拥有的模块权限
DEFAULT_MODULES = ["dashboard", "ai-report", "risk-query", "kyc-report", "chargeback-report"]



class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # Lark user_id
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    avatar_url = Column(String, nullable=True)
    lark_open_id = Column(String, unique=True, nullable=False)
    lark_union_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    # 用户可访问的模块列表（JSON 数组），如 ["dashboard","ai-report"]
    permitted_modules = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), onupdate=func.now())
