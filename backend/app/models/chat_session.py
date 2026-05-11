"""Chat session model for persisting AI report conversations."""
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.sql import func
import uuid
from ..database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, default="anonymous")
    title = Column(String, nullable=False, default="新对话")
    messages = Column(JSON, nullable=False, default=list)  # Full message history
    project_id = Column(String, nullable=True, default="105")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
