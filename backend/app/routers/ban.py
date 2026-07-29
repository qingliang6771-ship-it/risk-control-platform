"""封禁管理 (Ban Management) 路由。

接口：
- GET  /api/bans                 列表查询（支持 bundle_id / app_user_id / ban_level 筛选、分页）
- POST /api/bans                 单条录入
- POST /api/bans/batch           批量上传（Excel/CSV，返回成功/失败明细）
- GET  /api/bans/options         下拉选项（BundleID 列表、封禁等级列表）
- GET  /api/bans/template        下载批量导入模板（CSV）
- POST /api/bans/fund-info       「获取资金信息」占位接口（未来对接资金/支付中心）

所有接口都要求登录，并需要 `ban-management` 模块权限。
操作人从登录态 (token -> User) 提取，前端无需传。
"""
import io
import csv
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_db
from ..models.user import User
from ..models.ban import BanRecord, BAN_LEVELS, BAN_LEVEL_LABELS
from .auth import get_current_user_dep

router = APIRouter(prefix="/api/bans", tags=["ban-management"])


# BundleID 候选（可按需扩展/后续从配置或数据表读取）
BUNDLE_IDS = [
    "com.company.app1",
    "com.company.app2",
    "com.company.app3",
]


# ---------- 权限校验 ----------
async def require_ban_module(current_user: User = Depends(get_current_user_dep)) -> User:
    """要求用户拥有『封禁管理』模块权限（管理员放行）。"""
    modules = current_user.permitted_modules or []
    if not current_user.is_admin and "ban-management" not in modules:
        raise HTTPException(status_code=403, detail="没有『封禁管理』模块权限")
    return current_user


# ---------- Pydantic Schema ----------
class BanCreate(BaseModel):
    bundle_id: Optional[str] = None
    app_user_id: str = Field(..., min_length=1)
    payment_center_user_id: str = Field(..., min_length=1)
    ban_level: str = "warning"
    ban_reason: str = Field(..., min_length=1)
    total_recharge: float = 0
    total_withdraw: float = 0
    total_risk_amount: float = 0
    current_balance: float = 0
    balance_refunded: bool = False


class FundInfoQuery(BaseModel):
    app_user_id: Optional[str] = None
    payment_center_user_id: Optional[str] = None


# ---------- 工具 ----------
def _validate_level(level: str) -> str:
    if level not in BAN_LEVELS:
        raise HTTPException(status_code=400, detail=f"无效封禁等级: {level}")
    return level


def _to_float(v, default=0.0):
    if v is None or v == "":
        return default
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "是", "已退", "已退余额")


# ---------- 选项 ----------
@router.get("/options")
async def get_options(_: User = Depends(require_ban_module)):
    """返回下拉选项：BundleID 列表 + 封禁等级列表。"""
    return {
        "bundle_ids": BUNDLE_IDS,
        "ban_levels": [{"key": k, "label": BAN_LEVEL_LABELS[k]} for k in BAN_LEVELS],
    }


# ---------- 资金信息占位 ----------
@router.post("/fund-info")
async def fetch_fund_info(body: FundInfoQuery, _: User = Depends(require_ban_module)):
    """『获取资金信息』占位接口。

    未来在此对接资金中心 / 支付中心，根据用户ID回填资金数据。
    目前返回全 0 占位，前端可据此回填字段。
    """
    if not body.app_user_id and not body.payment_center_user_id:
        raise HTTPException(status_code=400, detail="请先填写业务用户ID或支付中心用户ID")
    # TODO: 对接真实资金/支付中心接口
    return {
        "ok": True,
        "source": "placeholder",
        "data": {
            "total_recharge": 0,
            "total_withdraw": 0,
            "total_risk_amount": 0,
            "current_balance": 0,
        },
        "message": "资金信息接口尚未接入，当前返回占位数据。",
    }


# ---------- 列表查询 ----------
@router.get("")
async def list_bans(
    bundle_id: Optional[str] = None,
    app_user_id: Optional[str] = None,
    ban_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_ban_module),
):
    """分页列表查询，支持按 BundleID / 业务用户ID / 封禁等级筛选。"""
    stmt = select(BanRecord)
    count_stmt = select(func.count(BanRecord.id))

    if bundle_id:
        stmt = stmt.where(BanRecord.bundle_id == bundle_id)
        count_stmt = count_stmt.where(BanRecord.bundle_id == bundle_id)
    if app_user_id:
        like = f"%{app_user_id}%"
        stmt = stmt.where(BanRecord.app_user_id.ilike(like))
        count_stmt = count_stmt.where(BanRecord.app_user_id.ilike(like))
    if ban_level:
        stmt = stmt.where(BanRecord.ban_level == ban_level)
        count_stmt = count_stmt.where(BanRecord.ban_level == ban_level)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(BanRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [r.to_dict() for r in rows],
    }


# ---------- 单条录入 ----------
@router.post("")
async def create_ban(
    body: BanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ban_module),
):
    """手动录入一条封禁记录。操作人从登录态提取。"""
    _validate_level(body.ban_level)

    record = BanRecord(
        bundle_id=body.bundle_id or None,
        app_user_id=body.app_user_id.strip(),
        payment_center_user_id=body.payment_center_user_id.strip(),
        ban_level=body.ban_level,
        ban_reason=body.ban_reason.strip(),
        total_recharge=body.total_recharge,
        total_withdraw=body.total_withdraw,
        total_risk_amount=body.total_risk_amount,
        current_balance=body.current_balance,
        balance_refunded=body.balance_refunded,
        operator_id=current_user.id,
        operator_name=current_user.name,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record.to_dict()


# ---------- 批量上传 ----------
# 模板列（表头 -> 字段）。表头用中文，便于风控同事填写。
TEMPLATE_COLUMNS = [
    ("BundleID", "bundle_id"),
    ("业务用户ID", "app_user_id"),
    ("支付中心用户ID", "payment_center_user_id"),
    ("封禁等级", "ban_level"),
    ("封禁原因", "ban_reason"),
    ("累计充值", "total_recharge"),
    ("累计提现", "total_withdraw"),
    ("累计风险金额", "total_risk_amount"),
    ("当前余额", "current_balance"),
    ("是否已退余额", "balance_refunded"),
]

# 等级中文 -> key 反查
LEVEL_LABEL_TO_KEY = {v: k for k, v in BAN_LEVEL_LABELS.items()}


def _parse_level(raw) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s in BAN_LEVELS:
        return s
    if s in LEVEL_LABEL_TO_KEY:
        return LEVEL_LABEL_TO_KEY[s]
    return None  # 无法识别


def _rows_from_csv(content: bytes) -> List[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def _rows_from_xlsx(content: bytes) -> List[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return []
    header = [str(h).strip() if h is not None else "" for h in header]
    out = []
    for r in rows_iter:
        if r is None:
            continue
        row = {header[i]: r[i] for i in range(min(len(header), len(r)))}
        # 跳过整行空
        if all((v is None or str(v).strip() == "") for v in row.values()):
            continue
        out.append(row)
    return out


@router.post("/batch")
async def batch_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ban_module),
):
    """批量上传封禁记录（.xlsx / .csv）。

    返回：成功条数、失败条数、以及每个失败行的行号与原因。
    """
    filename = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    try:
        if filename.endswith(".csv"):
            rows = _rows_from_csv(content)
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            rows = _rows_from_xlsx(content)
        else:
            raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .csv 文件")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有可导入的数据行")

    # 中文表头 -> 字段名 映射
    header_map = {cn: field for cn, field in TEMPLATE_COLUMNS}

    success = 0
    errors = []
    to_add = []

    for idx, raw in enumerate(rows, start=2):  # 从第 2 行开始（1 是表头）
        # 兼容中文表头或英文字段名两种
        def get(field_cn, field_en):
            if field_cn in raw:
                return raw.get(field_cn)
            return raw.get(field_en)

        app_user_id = get("业务用户ID", "app_user_id")
        pc_user_id = get("支付中心用户ID", "payment_center_user_id")
        reason = get("封禁原因", "ban_reason")
        level_raw = get("封禁等级", "ban_level")

        row_errors = []
        app_user_id = str(app_user_id).strip() if app_user_id not in (None, "") else ""
        pc_user_id = str(pc_user_id).strip() if pc_user_id not in (None, "") else ""
        reason = str(reason).strip() if reason not in (None, "") else ""

        if not app_user_id:
            row_errors.append("业务用户ID 必填")
        if not pc_user_id:
            row_errors.append("支付中心用户ID 必填")
        if not reason:
            row_errors.append("封禁原因 必填")

        level = _parse_level(level_raw) or "warning"

        if row_errors:
            errors.append({"row": idx, "reasons": row_errors})
            continue

        record = BanRecord(
            bundle_id=(str(get("BundleID", "bundle_id")).strip() or None) if get("BundleID", "bundle_id") else None,
            app_user_id=app_user_id,
            payment_center_user_id=pc_user_id,
            ban_level=level,
            ban_reason=reason,
            total_recharge=_to_float(get("累计充值", "total_recharge")),
            total_withdraw=_to_float(get("累计提现", "total_withdraw")),
            total_risk_amount=_to_float(get("累计风险金额", "total_risk_amount")),
            current_balance=_to_float(get("当前余额", "current_balance")),
            balance_refunded=_to_bool(get("是否已退余额", "balance_refunded")),
            operator_id=current_user.id,
            operator_name=current_user.name,
        )
        to_add.append(record)
        success += 1

    if to_add:
        db.add_all(to_add)
        await db.commit()

    return {
        "total": len(rows),
        "success": success,
        "failed": len(errors),
        "errors": errors,
    }


# ---------- 模板下载 ----------
@router.get("/template")
async def download_template(_: User = Depends(require_ban_module)):
    """下载批量导入 CSV 模板（含表头与一行示例）。"""
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [cn for cn, _ in TEMPLATE_COLUMNS]
    writer.writerow(headers)
    # 示例行
    writer.writerow([
        "com.company.app1", "U100001", "PC100001", "永久封禁",
        "多账号套利", "1000", "800", "500", "200", "否",
    ])
    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")  # BOM 保证 Excel 中文不乱码
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ban_import_template.csv"},
    )
