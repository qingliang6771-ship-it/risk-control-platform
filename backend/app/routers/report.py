"""Report router - AI + ThinkingData data report endpoints."""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from ..services.ai_report import ai_report_service


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
async def chat_stream(request: ChatStreamRequest):
    """Streaming AI chat for data analysis. Returns SSE stream."""
    try:
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
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
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
