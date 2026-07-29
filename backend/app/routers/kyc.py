"""KYC 统计报告路由 - Excel 上传、按月查询。"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Optional

from ..services import kyc_report

router = APIRouter(prefix="/api/kyc-report", tags=["kyc"])


@router.get("")
async def get_kyc_report(month: Optional[str] = Query(None, description="月份 YYYY-MM，不传返回最新")):
    """
    获取 KYC 统计报告数据。
    - 不传 month：返回最近一次上传的（最新月份）数据。
    - 传 month（YYYY-MM）：返回对应月份数据。
    """
    payload = kyc_report.get_report(month)
    if payload is None:
        raise HTTPException(status_code=404, detail="暂无数据，请先上传 Excel")
    return payload


@router.get("/months")
async def list_kyc_months():
    """列出所有已上传的月份（降序）。"""
    return {"months": kyc_report.list_months()}


@router.post("/upload")
async def upload_kyc_excel(
    file: UploadFile = File(...),
    month: Optional[str] = Query(None, description="指定月份 YYYY-MM，不传则从数据自动推断"),
):
    """
    上传每月 KYC Excel 文件。解析后按月份存储，并返回解析结果。
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 文件")

    try:
        content = await file.read()
        data = kyc_report.parse_excel(content, month=month)
        target_month = data["meta"]["month"]
        kyc_report.save_report(data, target_month)
        return {
            "ok": True,
            "month": target_month,
            "summary": data["summary"],
            "meta": data["meta"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
