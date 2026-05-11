"""Report router - AI + ThinkingData data report endpoints with session management."""
import json
import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update

from ..services.ai_report import ai_report_service
from ..database import get_db
from ..models.query_log import QueryLog
from ..models.chat_session import ChatSession


router = APIRouter(prefix="/api/report", tags=["report"])


class QuestionRequest(BaseModel):
    question: str


class SQLRequest(BaseModel):
    sql: str


class GenerateRequest(BaseModel):
    query: str
    context: Optional[str] = None


class ChatStreamRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    history: Optional[List[dict]] = None


class SessionCreateRequest(BaseModel):
    title: Optional[str] = "新对话"
    project_id: Optional[str] = "105"


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[dict]] = None


# ==================== Session APIs ====================

@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions, ordered by last updated."""
    result = await db.execute(
        select(ChatSession).order_by(desc(ChatSession.updated_at)).limit(100)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "project_id": s.project_id,
            "message_count": len(s.messages) if s.messages else 0,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@router.post("/sessions")
async def create_session(request: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new chat session."""
    session = ChatSession(
        title=request.title,
        project_id=request.project_id,
        messages=[],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "project_id": session.project_id,
        "messages": session.messages,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific session with full message history."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "project_id": session.project_id,
        "messages": session.messages or [],
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update session title or messages."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if request.title is not None:
        session.title = request.title
    if request.messages is not None:
        session.messages = request.messages
    await db.commit()
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chat session."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
    return {"ok": True}


# ==================== Chat APIs ====================

@router.post("/generate")
async def generate_report(request: GenerateRequest):
    """AI-powered data query: natural language -> SQL -> ThinkingData -> AI analysis."""
    try:
        result = await ai_report_service.generate_report(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatStreamRequest, db: AsyncSession = Depends(get_db)):
    """Streaming AI chat for data analysis. Returns SSE stream. Saves to session."""
    try:
        start_time = time.time()

        async def event_generator():
            full_result = {}
            try:
                yield f"data: {json.dumps({'type': 'status', 'content': '正在分析您的问题...'}, ensure_ascii=False)}\n\n"
                result = await ai_report_service.generate_report(request.query)
                full_result = result
                if result.get("sql"):
                    yield f"data: {json.dumps({'type': 'sql', 'content': result['sql']}, ensure_ascii=False)}\n\n"
                if result.get("data"):
                    yield f"data: {json.dumps({'type': 'data', 'content': result['data']}, ensure_ascii=False)}\n\n"
                if result.get("analysis"):
                    yield f"data: {json.dumps({'type': 'analysis', 'content': result['analysis']}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

                # Save to session if session_id provided
                if request.session_id:
                    try:
                        res = await db.execute(select(ChatSession).where(ChatSession.id == request.session_id))
                        session = res.scalar_one_or_none()
                        if session:
                            msgs = session.messages or []
                            # Add user message
                            msgs.append({"role": "user", "content": request.query})
                            # Add assistant message with parts
                            parts = []
                            if result.get("sql"):
                                parts.append({"type": "sql", "content": result["sql"]})
                            if result.get("data"):
                                parts.append({"type": "data", "content": result["data"]})
                            if result.get("analysis"):
                                parts.append({"type": "analysis", "content": result["analysis"]})
                            msgs.append({"role": "assistant", "content": result.get("analysis", ""), "parts": parts})
                            session.messages = msgs
                            # Auto-title from first query
                            if session.title == "新对话" and len(msgs) <= 2:
                                session.title = request.query[:30] + ("..." if len(request.query) > 30 else "")
                            await db.commit()
                    except Exception as e:
                        print(f"Failed to save session: {e}")

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Legacy APIs ====================

@router.get("/history")
async def get_report_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get AI report query history (legacy - from query_logs)."""
    try:
        result = await db.execute(
            select(QueryLog)
            .where(QueryLog.query_type == "ai_report")
            .order_by(desc(QueryLog.created_at))
            .limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "query": log.query_input,
                "result": log.query_result,
                "status": log.status,
                "error": log.error_message,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{log_id}")
async def delete_history_item(log_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a specific history item."""
    try:
        result = await db.execute(select(QueryLog).where(QueryLog.id == log_id))
        log = result.scalar_one_or_none()
        if log:
            await db.delete(log)
            await db.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-query")
async def ai_query(request: QuestionRequest):
    """AI-powered data query (legacy endpoint)."""
    try:
        result = await ai_report_service.generate_report(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/direct-sql")
async def direct_sql(request: SQLRequest):
    """Directly execute a SQL query on ThinkingData without AI."""
    try:
        result = await ai_report_service.direct_sql_query(request.sql)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
