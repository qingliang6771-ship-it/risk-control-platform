"""封禁记录模型 (BanRecord)。

对应【封禁管理】模块，记录被风控封禁的用户及其资金画像、封禁等级/原因、操作人等。
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base

# 封禁等级枚举（与前端下拉一致）
BAN_LEVELS = ["warning", "limit_withdraw", "freeze", "permanent"]
BAN_LEVEL_LABELS = {
    "warning": "轻度警告",
    "limit_withdraw": "限制提现",
    "freeze": "冻结账户",
    "permanent": "永久封禁",
}


class BanRecord(Base):
    __tablename__ = "ban_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 标识信息
    bundle_id = Column(String, nullable=True, index=True)              # BundleID / 产品包
    app_user_id = Column(String, nullable=False, index=True)          # 业务用户ID
    payment_center_user_id = Column(String, nullable=False, index=True)  # 支付中心用户ID

    # 封禁信息
    ban_level = Column(String, nullable=False, default="warning")     # 封禁等级 key
    ban_reason = Column(Text, nullable=False)                         # 封禁原因

    # 资金数据
    total_recharge = Column(Float, nullable=True, default=0)          # 累计充值
    total_withdraw = Column(Float, nullable=True, default=0)          # 累计提现
    total_risk_amount = Column(Float, nullable=True, default=0)       # 累计风险金额
    current_balance = Column(Float, nullable=True, default=0)         # 当前余额

    # 是否已退余额
    balance_refunded = Column(Boolean, nullable=False, default=False)

    # 操作人（从登录态提取，不由前端手填）
    operator_id = Column(String, nullable=True)
    operator_name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bundle_id": self.bundle_id,
            "app_user_id": self.app_user_id,
            "payment_center_user_id": self.payment_center_user_id,
            "ban_level": self.ban_level,
            "ban_level_label": BAN_LEVEL_LABELS.get(self.ban_level, self.ban_level),
            "ban_reason": self.ban_reason,
            "total_recharge": self.total_recharge or 0,
            "total_withdraw": self.total_withdraw or 0,
            "total_risk_amount": self.total_risk_amount or 0,
            "current_balance": self.current_balance or 0,
            "balance_refunded": bool(self.balance_refunded),
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
