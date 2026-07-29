"""Chargeback 抗辩复核统计服务 - 解析每月上传的 Chargeback 复核 Excel 并按月份存储/查询。

数据流：管理员上传 Excel -> 解析清洗 -> 计算成前端所需的 D 结构 -> 按月份存为 JSON。
查询：不传月份返回最新，传月份返回对应月份。

数据来源：【菲律宾客服】Chargeback复核表
"""
import io
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional

import openpyxl

# 数据存储目录：backend/data/chargeback/{YYYY-MM}.json
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chargeback"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Excel 表头（按列顺序，与【菲律宾客服】Chargeback复核表 对应）
COL = {
    "order_no": 0,          # Order No
    "code": 1,              # code
    "seq": 2,               # 编号
    "assign_time": 3,       # 分配时间（黄平）
    "handle_time": 4,       # 处理时间
    "agent": 5,             # 处理人
    "temp_confirm": 6,      # Temp Confirm?
    "error_desc": 7,        # Error Description
    "cs_note": 8,           # 客服备注
    "review_result": 9,     # 复核结果 (Correct / ...)
    "review_note": 10,      # 复核人备注
    "return_cs": 11,        # 是否返回客服
    "reviewer": 12,         # 复核人
    "synced": 13,           # 是否已同步客服
    "second_done": 14,      # 客服是否完成二次处理
    "second_note": 15,      # 二次处理备注
    "cs_dispute": 16,       # 客服对复核结果的异议
    "assign_note": 17,      # 分配人备注
    "parent": 18,           # 父记录
    "chargeback": 19,       # 抗辩 (如 已提交7.29)
    "stat_field": 20,       # 统计字段
}


def _norm(v):
    """归一化单元格值为去空白字符串（None -> '')。"""
    if v is None:
        return ""
    return str(v).strip()


def _to_date(v):
    """把单元格转成 datetime.date，失败返回 None。"""
    if isinstance(v, datetime):
        return v.date()
    s = _norm(v)
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_excel(file_bytes: bytes, month: Optional[str] = None) -> dict:
    """
    解析 Chargeback 抗辩复核 Excel（bytes），返回前端所需的 D 结构。

    判定规则：
    - 每行 = 1 件抗辩复核（以 Order No 非空为准）。
    - 正确：复核结果 == 'Correct'。
    - 判断错误 judge_err：复核结果非空且 != 'Correct'（复核认为客服处理有误）。
    - 已提交抗辩 submitted：抗辩列包含 '已提交'。
    - 二次处理 second：客服是否完成二次处理 含 'yes'/'是'/'已'。
    - month：报告月份 YYYY-MM，不传则用处理时间里最多的月份自动推断。
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.worksheets[0]

    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or not _norm(r[COL["order_no"]]):
            continue
        rows.append(r)

    if not rows:
        raise ValueError("Excel 中没有有效数据行（Order No 列为空）")

    records = []
    for r in rows:
        def g(key):
            idx = COL[key]
            return r[idx] if idx < len(r) else None

        d = _to_date(g("handle_time")) or _to_date(g("assign_time"))
        review_result = _norm(g("review_result")).lower()
        chargeback = _norm(g("chargeback")).lower()
        second = _norm(g("second_done")).lower()

        is_correct = review_result == "correct"
        is_judge_err = (review_result != "") and (not is_correct)
        is_submitted = ("已提交" in chargeback) or ("submit" in chargeback)
        is_second = ("yes" in second) or ("是" in second) or ("已" in second)

        records.append({
            "date": d,
            "agent": _norm(g("agent")) or "未知",
            "reviewer": _norm(g("reviewer")) or "未知",
            "is_correct": is_correct,
            "judge_err": 1 if is_judge_err else 0,
            "submitted": 1 if is_submitted else 0,
            "second": 1 if is_second else 0,
        })

    # 推断月份
    dates = [rec["date"] for rec in records if rec["date"]]
    if not month:
        if dates:
            month_counter = defaultdict(int)
            for d in dates:
                month_counter[d.strftime("%Y-%m")] += 1
            month = max(month_counter, key=month_counter.get)
        else:
            month = datetime.now().strftime("%Y-%m")

    # ---------- 每日聚合 ----------
    day_map = defaultdict(lambda: {"vol": 0, "correct": 0, "judge_err": 0, "submitted": 0})
    for rec in records:
        if not rec["date"]:
            continue
        key = rec["date"].strftime("%m-%d")
        dm = day_map[key]
        dm["vol"] += 1
        dm["correct"] += 1 if rec["is_correct"] else 0
        dm["judge_err"] += rec["judge_err"]
        dm["submitted"] += rec["submitted"]

    daily_vol = []
    daily_acc = []
    for key in sorted(day_map.keys()):
        dm = day_map[key]
        daily_vol.append({"date": key, "vol": dm["vol"]})
        acc = round(dm["correct"] / dm["vol"] * 100, 2) if dm["vol"] else 0.0
        daily_acc.append({
            "date": key,
            "acc": acc,
            "judge_err": dm["judge_err"],
            "submitted": dm["submitted"],
        })

    # ---------- 客服（处理人）聚合 ----------
    agent_map = defaultdict(lambda: {
        "total": 0, "correct": 0, "judge_err": 0, "submitted": 0, "second": 0, "days": set()
    })
    for rec in records:
        am = agent_map[rec["agent"]]
        am["total"] += 1
        am["correct"] += 1 if rec["is_correct"] else 0
        am["judge_err"] += rec["judge_err"]
        am["submitted"] += rec["submitted"]
        am["second"] += rec["second"]
        if rec["date"]:
            am["days"].add(rec["date"])

    agents = []
    for name, am in agent_map.items():
        total = am["total"]
        days = len(am["days"]) or 1
        avg = round(total / days, 1)
        acc = round(am["correct"] / total * 100, 2) if total else 0.0
        sub_rate = round(am["submitted"] / total * 100, 2) if total else 0.0
        agents.append({
            "name": name, "total": total, "days": days, "avg": avg, "acc": acc,
            "submitted": am["submitted"], "sub_rate": sub_rate,
            "judge_err": am["judge_err"], "second": am["second"],
        })
    agents.sort(key=lambda x: x["total"], reverse=True)

    # ---------- 汇总 ----------
    total = len(records)
    correct = sum(1 for r in records if r["is_correct"])
    judge_err = sum(r["judge_err"] for r in records)
    submitted = sum(r["submitted"] for r in records)
    second = sum(r["second"] for r in records)
    summary = {
        "总复核量": float(total),
        "正确数": float(correct),
        "正确率(%)": round(correct / total * 100, 2) if total else 0.0,
        "判断错误数": float(judge_err),
        "判断错误占比(%)": round(judge_err / total * 100, 2) if total else 0.0,
        "已提交抗辩数": float(submitted),
        "抗辩提交率(%)": round(submitted / total * 100, 2) if total else 0.0,
        "二次处理数": float(second),
    }

    n_days = len(day_map) or 1
    meta = {
        "daily_vol_avg": round(total / n_days, 1),
        "n_agents": len(agent_map),
        "n_days": len(day_map),
        "month": month,
    }

    return {
        "daily_vol": daily_vol,
        "daily_acc": daily_acc,
        "agents": agents,
        "summary": summary,
        "meta": meta,
    }


def _month_file(month: str) -> Path:
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise ValueError("月份格式应为 YYYY-MM")
    return DATA_DIR / f"{month}.json"


def save_report(data: dict, month: str) -> None:
    """把解析后的数据按月份存为 JSON 文件。"""
    payload = {
        "month": month,
        "uploaded_at": datetime.now().isoformat(),
        "data": data,
    }
    with open(_month_file(month), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def list_months():
    """列出所有已存在的月份，降序。"""
    months = [p.stem for p in DATA_DIR.glob("*.json")]
    months.sort(reverse=True)
    return months


def get_report(month: Optional[str] = None):
    """读取指定月份数据；不传则返回最新月份。返回 None 表示无数据。"""
    months = list_months()
    if not months:
        return None
    target = month if month else months[0]
    fp = _month_file(target)
    if not fp.exists():
        return None
    with open(fp, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload
