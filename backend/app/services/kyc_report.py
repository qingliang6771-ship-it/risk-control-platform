"""KYC 统计报告服务 - 解析每月上传的 KYC Excel 并按月份存储/查询。

数据流：管理员上传 Excel -> 解析清洗 -> 计算成前端所需的 D 结构 -> 按月份存为 JSON。
查询：不传月份返回最新，传月份返回对应月份。
"""
import io
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional

import openpyxl

# 数据存储目录：backend/data/kyc/{YYYY-MM}.json
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kyc"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Excel 表头（按顺序）
COL = {
    "applicant": 0,        # Applicant ID
    "handle_time": 1,      # 客服处理时间
    "agent": 2,            # 处理人（客服）
    "cs_result": 3,        # 客服处理结果 (request check / reject)
    "cs_note": 4,          # 客服备注
    "only_warning": 5,     # only warning/pep/fitness probity
    "review_result": 6,    # 复核结果 (Correct / ...)
    "review_note": 7,      # 复核人备注
    "reviewer": 8,         # 复核人
    "review_op": 9,        # 复核人操作 (reject, method 1 / method 2 / 空)
    "synced": 10,          # 是否已同步客服
    "cs_dispute": 11,      # 客服对复核结果的异议
    "assign_note": 12,     # 分配人备注
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
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_excel(file_bytes: bytes, month: Optional[str] = None) -> dict:
    """
    解析 KYC Excel（bytes），返回前端所需的 D 结构。

    判定规则：
    - 每行 = 1 个处理量（applicant）。
    - 正确：复核结果 == 'Correct'。
    - 判断错误 judge_err：复核结果 != 'Correct'（即复核认为客服判断有误）。
    - 操作错误 op_err：复核人操作中含 'method'（如 reject, method 1/2），表示操作层面纠正。
    - 拒绝 rej：客服处理结果 == 'reject'，或复核人操作以 'reject' 开头。
    - month：报告月份 YYYY-MM，不传则用数据里最多的月份自动推断。
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.worksheets[0]

    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or not _norm(r[COL["applicant"]]):
            continue
        rows.append(r)

    if not rows:
        raise ValueError("Excel 中没有有效数据行")

    # 逐行解析成标准记录
    records = []
    for r in rows:
        def g(key):
            idx = COL[key]
            return r[idx] if idx < len(r) else None

        d = _to_date(g("handle_time"))
        cs_result = _norm(g("cs_result")).lower()
        review_result = _norm(g("review_result")).lower()
        review_op = _norm(g("review_op")).lower()

        is_correct = review_result == "correct"
        is_judge_err = (review_result != "") and (not is_correct)
        is_op_err = "method" in review_op
        is_reject = cs_result == "reject" or review_op.startswith("reject")

        records.append({
            "date": d,
            "agent": _norm(g("agent")) or "未知",
            "is_correct": is_correct,
            "judge_err": 1 if is_judge_err else 0,
            "op_err": 1 if is_op_err else 0,
            "reject": 1 if is_reject else 0,
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
    day_map = defaultdict(lambda: {"vol": 0, "correct": 0, "judge_err": 0, "op_err": 0})
    for rec in records:
        if not rec["date"]:
            continue
        key = rec["date"].strftime("%m-%d")
        dm = day_map[key]
        dm["vol"] += 1
        dm["correct"] += 1 if rec["is_correct"] else 0
        dm["judge_err"] += rec["judge_err"]
        dm["op_err"] += rec["op_err"]

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
            "op_err": dm["op_err"],
        })

    # ---------- 客服聚合 ----------
    agent_map = defaultdict(lambda: {
        "total": 0, "correct": 0, "judge_err": 0, "op_err": 0, "reject": 0, "days": set()
    })
    for rec in records:
        am = agent_map[rec["agent"]]
        am["total"] += 1
        am["correct"] += 1 if rec["is_correct"] else 0
        am["judge_err"] += rec["judge_err"]
        am["op_err"] += rec["op_err"]
        am["reject"] += rec["reject"]
        if rec["date"]:
            am["days"].add(rec["date"])

    agent_vol = []
    agent_qa = []
    agents = []
    for name, am in agent_map.items():
        total = am["total"]
        days = len(am["days"]) or 1
        avg = round(total / days, 1)
        acc = round(am["correct"] / total * 100, 2) if total else 0.0
        rej = am["reject"]
        rej_rate = round(rej / total * 100, 2) if total else 0.0
        agent_vol.append({"agent": name, "total": total, "days": days, "avg": avg})
        agent_qa.append({
            "agent": name, "total": total, "acc": acc, "rej": rej,
            "rej_rate": rej_rate, "op_err": am["op_err"], "judge_err": am["judge_err"],
        })
        agents.append({
            "name": name, "total": total, "days": days, "avg": avg, "acc": acc,
            "rej": rej, "rej_rate": rej_rate, "judge_err": am["judge_err"], "op_err": am["op_err"],
        })

    # 按处理量降序
    agent_vol.sort(key=lambda x: x["total"], reverse=True)
    agent_qa.sort(key=lambda x: x["total"], reverse=True)
    agents.sort(key=lambda x: x["total"], reverse=True)

    # ---------- 汇总 ----------
    total = len(records)
    correct = sum(1 for r in records if r["is_correct"])
    op_err = sum(r["op_err"] for r in records)
    judge_err = sum(r["judge_err"] for r in records)
    reject = sum(r["reject"] for r in records)
    summary = {
        "总处理量": float(total),
        "正确数": float(correct),
        "正确率(%)": round(correct / total * 100, 2) if total else 0.0,
        "操作错误数": float(op_err),
        "操作错误占比(%)": round(op_err / total * 100, 2) if total else 0.0,
        "判断错误数": float(judge_err),
        "判断错误占比(%)": round(judge_err / total * 100, 2) if total else 0.0,
        "拒绝数": float(reject),
        "拒绝率(%)": round(reject / total * 100, 2) if total else 0.0,
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
        "agent_vol": agent_vol,
        "agent_qa": agent_qa,
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
