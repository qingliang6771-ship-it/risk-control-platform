"""Chat session model for persisting AI report conversations."""
import json
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
import uuid
from ..database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, default="anonymous")
    title = Column(String, nullable=False, default="新对话")
    _messages = Column("messages", Text, nullable=False, default="[]")  # JSON stored as text
    project_id = Column(String, nullable=True, default="105")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def messages(self):
        """Deserialize messages from JSON text."""
        if self._messages:
            try:
                return json.loads(self._messages)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @messages.setter
    def messages(self, value):
        """Serialize messages to JSON text."""
        if value is None:
            self._messages = "[]"
        elif isinstance(value, str):
            self._messages = value
        else:
            self._messages = json.dumps(value, ensure_ascii=False)
