"""根据学号规则生成股票代码。"""

from __future__ import annotations


def build_stock_code(student_id: str, market: str) -> str:
    """根据题目要求生成 Tushare 使用的股票代码。"""
    digits = "".join(ch for ch in student_id if ch.isdigit())
    if len(digits) < 3:
        raise ValueError("student_id 至少需要包含 3 位数字。")

    suffix = int(digits[-3:])
    market_lower = market.lower()
    if market_lower == "sh":
        code = 600000 + suffix
        return f"{code:06d}.SH"
    if market_lower == "sz":
        code = suffix
        return f"{code:06d}.SZ"
    raise ValueError("market 只能填写 sh 或 sz。")
