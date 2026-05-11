"""Query log model for tracking AI and risk queries."""
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.sql import func
import uuid
from ..database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    query_type = Column(String, nullable=False)  # "ai_report", "risk_score", "ta_query"
    query_input = Column(Text, nullable=False)
    query_result = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending, success, error
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
