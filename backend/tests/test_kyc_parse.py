"""生成一个符合格式的 KYC Excel 并验证 parse_excel 输出结构。
运行：python -m tests.test_kyc_parse   （在 backend 目录下）
"""
import io
import random
from datetime import date

import openpyxl

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import kyc_report

HEADER = [
    "Applicant ID", "客服处理时间", "处理人", "客服处理结果", "客服备注",
    "only warning/pep", "复核结果", "复核人备注", "复核人", "复核人操作",
    "是否已同步客服", "客服异议", "分配人备注",
]

AGENTS = ["Angel B", "Blessa", "Chesca M", "Shan T"]


def build_excel() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    random.seed(42)
    rid = 0
    for day in range(1, 21):  # 6月1-20日
        d = date(2025, 6, day)
        for _ in range(random.randint(8, 20)):
            rid += 1
            agent = random.choice(AGENTS)
            roll = random.random()
            if roll < 0.03:            # 判断错误
                review_result, review_op = "Wrong", ""
            elif roll < 0.05:          # 操作错误
                review_result, review_op = "Correct", "reject, method 1"
            else:
                review_result, review_op = "Correct", ""
            cs_result = "reject" if random.random() < 0.05 else "request check"
            ws.append([
                f"A{rid:05d}", d.strftime("%Y-%m-%d"), agent, cs_result, "",
                "", review_result, "", "Reviewer1", review_op, "yes", "", "",
            ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main():
    data = kyc_report.parse_excel(build_excel())
    print("=== meta ===", data["meta"])
    print("=== summary ===", data["summary"])
    assert "daily_vol" in data and data["daily_vol"], "缺少 daily_vol"
    assert "daily_acc" in data and data["daily_acc"], "缺少 daily_acc"
    assert "agents" in data and data["agents"], "缺少 agents"
    for k in ("总处理量", "正确率(%)", "拒绝率(%)", "操作错误数", "判断错误数"):
        assert k in data["summary"], f"summary 缺少 {k}"
    a = data["agents"][0]
    for k in ("name", "total", "days", "avg", "acc", "rej", "rej_rate", "judge_err", "op_err"):
        assert k in a, f"agent 缺少 {k}"
    assert "tat" not in a, "agent 不应含 tat（已移除时效）"
    assert "daily_tat" not in data, "不应含 daily_tat"
    print("=== agents[0] ===", a)
    print("\n✅ 解析结构验证通过，字段与前端一致，且已移除 TAT/email。")


if __name__ == "__main__":
    main()
