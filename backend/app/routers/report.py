"""Report router - AI + ThinkingData data report endpoints."""
import json
import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..services.ai_report import ai_report_service
from ..database import get_db
from ..models.query_log import QueryLog
from .auth import get_current_user_dep
from ..models.user import User


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
    history: Optional[List[dict]] = None


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
    """Streaming AI chat for data analysis. Returns SSE stream."""
    try:
        start_time = time.time()

        async def event_generator():
            try:
                yield f"data: {json.dumps({'type': 'status', 'content': '正在分析您的问题...'}, ensure_ascii=False)}\n\n"
                result = await ai_report_service.generate_report(request.query)
                if result.get("sql"):
                    yield f"data: {json.dumps({'type': 'sql', 'content': result['sql']}, ensure_ascii=False)}\n\n"
                if result.get("data"):
                    yield f"data: {json.dumps({'type': 'data', 'content': result['data']}, ensure_ascii=False)}\n\n"
                if result.get("analysis"):
                    yield f"data: {json.dumps({'type': 'analysis', 'content': result['analysis']}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

                # Save to history
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    log = QueryLog(
                        user_id="anonymous",
                        query_type="ai_report",
                        query_input=request.query,
                        query_result=result,
                        status="success",
                        duration_ms=duration_ms,
                    )
                    db.add(log)
                    await db.commit()
                except Exception:
                    pass

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
                # Save error to history
                try:
                    log = QueryLog(
                        user_id="anonymous",
                        query_type="ai_report",
                        query_input=request.query,
                        status="error",
                        error_message=str(e),
                        duration_ms=int((time.time() - start_time) * 1000),
                    )
                    db.add(log)
                    await db.commit()
                except Exception:
                    pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_report_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get AI report query history."""
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
