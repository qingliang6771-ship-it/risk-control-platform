"""Risk control query router."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..models.query_log import QueryLog
from ..services.risk_model import risk_model_service
from .auth import get_current_user_dep

router = APIRouter(prefix="/api/risk", tags=["risk"])


class RiskQueryRequest(BaseModel):
    user_id: str
    models: Optional[list[str]] = None  # specific models to query, None = all


@router.get("/score/{target_user_id}")
async def get_risk_score(
    target_user_id: str,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get risk score for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"risk_score:{target_user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_risk_score(target_user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud/{target_user_id}")
async def get_fraud_detection(
    target_user_id: str,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get fraud detection result for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"fraud_detection:{target_user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_fraud_detection(target_user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credit/{target_user_id}")
async def get_credit_assessment(
    target_user_id: str,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get credit assessment result for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"credit_assessment:{target_user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_credit_assessment(target_user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/behavior/{target_user_id}")
async def get_behavior_analysis(
    target_user_id: str,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get behavior analysis result for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"behavior_analysis:{target_user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_behavior_analysis(target_user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/{target_user_id}")
async def get_device_fingerprint(
    target_user_id: str,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get device fingerprint analysis for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"device_fingerprint:{target_user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_device_fingerprint(target_user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/all")
async def get_all_risk_models(
    request: RiskQueryRequest,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Get all risk model results for a specific user."""
    log = QueryLog(
        user_id=current_user.id,
        query_type="risk_score",
        query_input=f"all_models:{request.user_id}",
        status="pending",
    )
    db.add(log)
    await db.commit()

    try:
        result = await risk_model_service.get_all_models_result(request.user_id)
        log.query_result = result
        log.status = "success"
        await db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))
