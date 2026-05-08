"""Tushare 获取与数据库存储模块。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.db import DatabaseClient
from hw1_stock_analysis.utils import ensure_output_dirs


class TushareAccessError(RuntimeError):
    """Tushare 访问权限或接口调用异常。"""


def _get_tushare_pro(token: str):
    """延迟导入 tushare，避免在未安装依赖时影响其他模块。"""
    try:
        import tushare as ts
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("缺少 tushare，请先安装 requirements.txt 中的依赖。") from exc

    ts.set_token(token)
    return ts.pro_api()


def _resolve_fetch_start_date(config: RuntimeConfig, db_client: DatabaseClient) -> str:
    """根据数据库中已有数据决定增量抓取起点。"""
    latest_trade_date = db_client.get_latest_trade_date(config.stock.ts_code)
    if not latest_trade_date:
        return config.app.start_date

    latest_dt = datetime.strptime(latest_trade_date, "%Y%m%d") + timedelta(days=1)
    return latest_dt.strftime("%Y%m%d")


def fetch_and_store_daily_data(config: RuntimeConfig, db_client: DatabaseClient) -> pd.DataFrame:
    """拉取指定区间的股票日线数据并执行增量存储。"""
    start_date = _resolve_fetch_start_date(config, db_client)
    if start_date > config.app.end_date:
        return pd.DataFrame()

    ensure_output_dirs(config.app.output_dir)
    pro = _get_tushare_pro(config.tushare_token)
    try:
        data = pro.daily(
            ts_code=config.stock.ts_code,
            start_date=start_date,
            end_date=config.app.end_date,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise TushareAccessError(_build_tushare_error_message(exc, config.stock.ts_code)) from exc
    if data.empty:
        return data

    data["trade_date"] = pd.to_datetime(data["trade_date"], format="%Y%m%d")
    data = data.sort_values("trade_date").reset_index(drop=True)
    now = datetime.now()
    rows = [
        (
            row.ts_code,
            row.trade_date.date(),
            row.open,
            row.high,
            row.low,
            row.close,
            row.pre_close,
            row.change,
            row.pct_chg,
            row.vol,
            row.amount,
            now,
            now,
        )
        for row in data.itertuples(index=False)
    ]
    db_client.upsert_daily_rows(rows)
    data.to_csv(
        config.app.output_dir / "data" / "raw_daily_from_tushare.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return data


def _build_tushare_error_message(exc: Exception, ts_code: str) -> str:
    """将 Tushare 原始异常转换为更可执行的提示。"""
    message = str(exc)
    if "daily" in message:
        return (
            "Tushare 已连通，但当前账号没有 `daily` 接口权限。\n"
            f"当前请求股票：{ts_code}\n"
            "根据 Tushare 官方权限说明，`daily` 日线接口至少需要 120 积分；"
            "120 积分档可访问股票非复权日线。\n"
            "如果你是全日制学生，Tushare 官方提供学生免费 2000 积分申请通道；"
            "申请通过后通常就足够完成本次作业。\n"
            "你可以先做两件事：\n"
            "1. 登录 Tushare 官网个人主页查看当前积分。\n"
            "2. 运行 `python check_tushare_access.py` 检查 token、积分到期信息和 daily 接口可用性。\n"
            "官方文档：\n"
            "- daily 权限说明：https://tushare.pro/document/1?doc_id=108\n"
            "- 积分频次表：https://tushare.pro/document/1?doc_id=290\n"
            "- 学生免费积分：https://tushare.pro/document/1?doc_id=360\n"
            f"原始错误：{message}"
        )
    return f"Tushare 接口调用失败：{message}"
