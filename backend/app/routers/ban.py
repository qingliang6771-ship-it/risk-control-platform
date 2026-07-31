"""封禁管理 (Ban Management) 路由。

接口：
- GET    /api/bans               列表查询（支持 bundle_id / app_user_id / ban_level / cleared 筛选、分页）
- POST   /api/bans               单条录入
- DELETE /api/bans/{ban_id}      删除记录（仅管理员）
- POST   /api/bans/batch         批量上传（Excel/CSV，返回成功/失败明细）
- GET    /api/bans/options       下拉选项（封禁类型列表）
- GET    /api/bans/stats         统计看板（总人数 / 各类型分布 / 周汇总 / 月汇总 / 清退情况）
- GET    /api/bans/template      下载批量导入模板（CSV）
- POST   /api/bans/fund-info     「获取资金信息」占位接口（未来对接资金/支付中心）

所有接口都要求登录，并需要 `ban-management` 模块权限。
删除接口额外要求管理员。
操作人从登录态 (token -> User) 提取，前端无需传。
"""
import io
import csv
from typing import Optional, List
from datetime import datetime, timedelta

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


# ---------- 权限校验 ----------
async def require_ban_module(current_user: User = Depends(get_current_user_dep)) -> User:
    """要求用户拥有『封禁管理』模块权限（管理员放行）。"""
    modules = current_user.permitted_modules or []
    if not current_user.is_admin and "ban-management" not in modules:
        raise HTTPException(status_code=403, detail="没有『封禁管理』模块权限")
    return current_user


async def require_admin_user(current_user: User = Depends(get_current_user_dep)) -> User:
    """删除等敏感操作要求管理员。"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可执行该操作")
    return current_user


# ---------- Pydantic Schema ----------
class BanCreate(BaseModel):
    cleared: bool = False
    bundle_id: Optional[str] = None
    app_user_id: str = Field(..., min_length=1)
    payment_center_user_id: str = Field(..., min_length=1)
    ban_level: str = "compliance"
    ban_reason: str = Field(..., min_length=1)
    total_recharge: float = 0
    total_withdraw: float = 0
    total_risk_amount: float = 0
    current_balance: float = 0
    balance_refunded: bool = False


class FundInfoQuery(BaseModel):
    app_user_id: Optional[str] = None
    payment_center_user_id: Optional[str] = None


class BanUpdate(BaseModel):
    """更新封禁记录：所有字段可选，仅更新传入的字段（部分更新）。"""
    cleared: Optional[bool] = None
    bundle_id: Optional[str] = None
    app_user_id: Optional[str] = None
    payment_center_user_id: Optional[str] = None
    ban_level: Optional[str] = None
    ban_reason: Optional[str] = None
    total_recharge: Optional[float] = None
    total_withdraw: Optional[float] = None
    total_risk_amount: Optional[float] = None
    current_balance: Optional[float] = None
    balance_refunded: Optional[bool] = None



# ---------- 工具 ----------
def _validate_level(level: str) -> str:
    if level not in BAN_LEVELS:
        raise HTTPException(status_code=400, detail=f"无效封禁类型: {level}")
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
    return s in ("1", "true", "yes", "y", "是", "已退", "已退余额", "已清退", "完成")


def _parse_date(s: Optional[str], end: bool = False) -> Optional[datetime]:
    """解析 YYYY-MM-DD 字符串为 datetime。end=True 时取当天 23:59:59。"""
    if not s:
        return None
    try:
        d = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
        if end:
            d = d.replace(hour=23, minute=59, second=59, microsecond=999999)
        return d
    except (ValueError, TypeError):
        return None


def _apply_common_filters(stmt, *, bundle_id=None, app_user_id=None, ban_level=None,
                          cleared=None, start_dt=None, end_dt=None):
    """把通用筛选条件应用到查询语句（列表 / 统计 / 导出共用）。"""
    if bundle_id:
        stmt = stmt.where(BanRecord.bundle_id.ilike(f"%{bundle_id}%"))
    if app_user_id:
        stmt = stmt.where(BanRecord.app_user_id.ilike(f"%{app_user_id}%"))
    if ban_level:
        stmt = stmt.where(BanRecord.ban_level == ban_level)
    if cleared is not None:
        stmt = stmt.where(BanRecord.cleared.is_(cleared))
    if start_dt is not None:
        stmt = stmt.where(BanRecord.created_at >= start_dt)
    if end_dt is not None:
        stmt = stmt.where(BanRecord.created_at <= end_dt)
    return stmt



# ---------- 选项 ----------
@router.get("/options")
async def get_options(_: User = Depends(require_ban_module)):
    """返回下拉选项：封禁类型列表（BundleID 改为手动录入，不再返回固定列表）。"""
    return {
        "ban_levels": [{"key": k, "label": BAN_LEVEL_LABELS[k]} for k in BAN_LEVELS],
    }


# ---------- 统计看板 ----------
@router.get("/stats")
async def get_stats(
    bundle_id: Optional[str] = None,
    app_user_id: Optional[str] = None,
    ban_level: Optional[str] = None,
    cleared: Optional[bool] = None,
    start_date: Optional[str] = None,  # YYYY-MM-DD
    end_date: Optional[str] = None,    # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_ban_module),
):
    """统计看板数据（支持与列表一致的筛选条件，含时间范围）：
    - total: 符合条件的封禁总人数
    - cleared / not_cleared: 已清退 / 未清退人数
    - by_level: 各封禁类型人数分布
    - this_week / this_month: 本周 / 本月新增封禁人数（不受筛选影响，反映全局趋势）
    """
    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date, end=True)
    fkw = dict(bundle_id=bundle_id, app_user_id=app_user_id, ban_level=ban_level,
               cleared=cleared, start_dt=start_dt, end_dt=end_dt)

    total = (await db.execute(
        _apply_common_filters(select(func.count(BanRecord.id)), **fkw)
    )).scalar() or 0
    cleared_cnt = (await db.execute(
        _apply_common_filters(
            select(func.count(BanRecord.id)).where(BanRecord.cleared.is_(True)),
            **{**fkw, "cleared": None})
    )).scalar() or 0

    # 各类型分布（同样受筛选影响）
    level_rows = (await db.execute(
        _apply_common_filters(
            select(BanRecord.ban_level, func.count(BanRecord.id)), **fkw
        ).group_by(BanRecord.ban_level)
    )).all()
    level_counts = {lvl: cnt for lvl, cnt in level_rows}
    by_level = [
        {"key": k, "label": BAN_LEVEL_LABELS[k], "count": int(level_counts.get(k, 0))}
        for k in BAN_LEVELS
    ]

    # 本周 / 本月新增（全局趋势指标，不叠加筛选）
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_week = (await db.execute(
        select(func.count(BanRecord.id)).where(BanRecord.created_at >= week_start)
    )).scalar() or 0
    this_month = (await db.execute(
        select(func.count(BanRecord.id)).where(BanRecord.created_at >= month_start)
    )).scalar() or 0

    return {
        "total": int(total),
        "cleared": int(cleared_cnt),
        "not_cleared": int(total) - int(cleared_cnt),
        "by_level": by_level,
        "this_week": int(this_week),
        "this_month": int(this_month),
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
    cleared: Optional[bool] = None,
    start_date: Optional[str] = None,  # YYYY-MM-DD 按封禁时间起
    end_date: Optional[str] = None,    # YYYY-MM-DD 按封禁时间止
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_ban_module),
):
    """分页列表查询，支持按 BundleID / 业务用户ID / 封禁类型 / 是否清退 / 时间范围 筛选。"""
    fkw = dict(
        bundle_id=bundle_id, app_user_id=app_user_id, ban_level=ban_level,
        cleared=cleared, start_dt=_parse_date(start_date), end_dt=_parse_date(end_date, end=True),
    )
    stmt = _apply_common_filters(select(BanRecord), **fkw)
    count_stmt = _apply_common_filters(select(func.count(BanRecord.id)), **fkw)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(BanRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [r.to_dict() for r in rows],
    }


# ---------- 导出（按当前筛选导出全部为 CSV）----------
# 导出列（表头 -> to_dict 字段），含所有字段
EXPORT_COLUMNS = [
    ("ID", "id"),
    ("是否已清退完成", "cleared"),
    ("BundleID", "bundle_id"),
    ("业务用户ID", "app_user_id"),
    ("支付中心用户ID", "payment_center_user_id"),
    ("封禁类型", "ban_level_label"),
    ("封禁原因", "ban_reason"),
    ("累计充值", "total_recharge"),
    ("累计提现", "total_withdraw"),
    ("累计风险金额", "total_risk_amount"),
    ("当前余额", "current_balance"),
    ("是否已退余额", "balance_refunded"),
    ("操作人", "operator_name"),
    ("封禁时间", "created_at"),
]


@router.get("/export")
async def export_bans(
    bundle_id: Optional[str] = None,
    app_user_id: Optional[str] = None,
    ban_level: Optional[str] = None,
    cleared: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_ban_module),
):
    """按当前筛选条件导出全部封禁记录为 CSV（不分页）。"""
    fkw = dict(
        bundle_id=bundle_id, app_user_id=app_user_id, ban_level=ban_level,
        cleared=cleared, start_dt=_parse_date(start_date), end_dt=_parse_date(end_date, end=True),
    )
    stmt = _apply_common_filters(select(BanRecord), **fkw).order_by(BanRecord.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([cn for cn, _ in EXPORT_COLUMNS])
    for r in rows:
        d = r.to_dict()
        line = []
        for _, field in EXPORT_COLUMNS:
            v = d.get(field)
            if field == "cleared":
                v = "已清退" if v else "未清退"
            elif field == "balance_refunded":
                v = "是" if v else "否"
            elif field == "created_at" and v:
                v = str(v).replace("T", " ")[:19]
            line.append("" if v is None else v)
        writer.writerow(line)

    filename = f"ban_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



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
        cleared=body.cleared,
        bundle_id=(body.bundle_id.strip() if body.bundle_id else None) or None,
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


# ---------- 更新（有模块权限即可）----------
@router.put("/{ban_id}")
async def update_ban(
    ban_id: int,
    body: BanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ban_module),
):
    """更新一条封禁记录（部分更新，仅更新传入字段）。可用于修改清退状态、封禁类型、资金数据等。"""
    record = (await db.execute(select(BanRecord).where(BanRecord.id == ban_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    data = body.dict(exclude_unset=True)

    if "ban_level" in data and data["ban_level"] is not None:
        _validate_level(data["ban_level"])
    # 必填字段不允许被清空
    for req in ("app_user_id", "payment_center_user_id", "ban_reason"):
        if req in data:
            v = (data[req] or "").strip() if isinstance(data[req], str) else data[req]
            if not v:
                raise HTTPException(status_code=400, detail=f"{req} 不能为空")
            data[req] = v
    # bundle_id 允许清空为 None
    if "bundle_id" in data:
        data["bundle_id"] = (data["bundle_id"].strip() if data["bundle_id"] else None) or None

    for k, v in data.items():
        setattr(record, k, v)

    await db.commit()
    await db.refresh(record)
    return record.to_dict()


# ---------- 删除（仅管理员）----------
@router.delete("/{ban_id}")
async def delete_ban(
    ban_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin_user),
):

    """删除一条封禁记录（仅管理员）。"""
    record = (await db.execute(select(BanRecord).where(BanRecord.id == ban_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.commit()
    return {"ok": True, "deleted_id": ban_id}


# ---------- 批量上传 ----------
# 模板列（表头 -> 字段）。表头用中文，便于风控同事填写。
TEMPLATE_COLUMNS = [
    ("是否已清退完成", "cleared"),
    ("BundleID", "bundle_id"),
    ("业务用户ID", "app_user_id"),
    ("支付中心用户ID", "payment_center_user_id"),
    ("封禁类型", "ban_level"),
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
        level_raw = get("封禁类型", "ban_level")

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

        level = _parse_level(level_raw)
        if level_raw not in (None, "") and level is None:
            row_errors.append(f"封禁类型无法识别: {level_raw}")
        level = level or "compliance"

        if row_errors:
            errors.append({"row": idx, "reasons": row_errors})
            continue

        bundle_raw = get("BundleID", "bundle_id")
        record = BanRecord(
            cleared=_to_bool(get("是否已清退完成", "cleared")),
            bundle_id=(str(bundle_raw).strip() or None) if bundle_raw else None,
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
        "否", "com.company.app1", "U100001", "PC100001", "合规封禁",
        "多账号套利", "1000", "800", "500", "200", "否",
    ])
    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")  # BOM 保证 Excel 中文不乱码
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ban_import_template.csv"},
    )
