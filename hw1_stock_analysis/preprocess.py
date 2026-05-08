"""数据清洗、特征工程与多时间粒度聚合。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.utils import ensure_output_dirs


@dataclass(frozen=True)
class ProcessedData:
    """预处理后的各层级数据结果。"""

    daily: pd.DataFrame
    weekly: pd.DataFrame
    monthly: pd.DataFrame
    yearly: pd.DataFrame


def preprocess_daily_data(daily_df: pd.DataFrame, config: RuntimeConfig) -> ProcessedData:
    """执行缺失值处理、异常值修正和衍生指标计算。"""
    if daily_df.empty:
        raise ValueError(
            "数据库中没有可分析的数据。"
            f"当前股票代码 {config.stock.ts_code} 在 {config.app.start_date}-{config.app.end_date} "
            "没有读到日线记录。请确认已经成功抓取数据；如果学号自动映射出的股票没有历史数据，"
            "请在 config.ini 的 stock.ts_code_override 中填写一个有数据的真实股票代码。"
        )

    ensure_output_dirs(config.app.output_dir)
    df = daily_df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    df[numeric_columns] = df[numeric_columns].interpolate().ffill().bfill()

    for column in ["open", "high", "low", "close", "vol", "amount"]:
        lower = df[column].quantile(0.01)
        upper = df[column].quantile(0.99)
        df[column] = df[column].clip(lower=lower, upper=upper)

    df["daily_return"] = df["close"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    df["ma5"] = df["close"].rolling(window=5, min_periods=1).mean()
    df["volume_volatility"] = df["vol"].rolling(window=5, min_periods=2).std().fillna(0.0)
    df["week"] = df["trade_date"].dt.to_period("W")
    df["month"] = df["trade_date"].dt.to_period("M")
    df["year"] = df["trade_date"].dt.to_period("Y")

    weekly_df = _aggregate_period(df, "week")
    monthly_df = _aggregate_period(df, "month")
    yearly_df = _aggregate_period(df, "year")

    data_dir = config.app.output_dir / "data"
    df.to_csv(data_dir / "processed_daily.csv", index=False, encoding="utf-8-sig")
    weekly_df.to_csv(data_dir / "weekly_agg.csv", index=False, encoding="utf-8-sig")
    monthly_df.to_csv(data_dir / "monthly_agg.csv", index=False, encoding="utf-8-sig")
    yearly_df.to_csv(data_dir / "yearly_agg.csv", index=False, encoding="utf-8-sig")
    return ProcessedData(daily=df, weekly=weekly_df, monthly=monthly_df, yearly=yearly_df)


def _aggregate_period(df: pd.DataFrame, period_column: str) -> pd.DataFrame:
    """按周、月、年统一聚合价格与成交量指标。"""
    grouped = df.groupby(period_column, as_index=False).agg(
        start_date=("trade_date", "min"),
        end_date=("trade_date", "max"),
        open=("open", "first"),
        close=("close", "last"),
        high=("high", "max"),
        low=("low", "min"),
        volume=("vol", "sum"),
        avg_daily_return=("daily_return", "mean"),
        return_std=("daily_return", "std"),
    )
    grouped[period_column] = grouped[period_column].astype(str)
    grouped["period_return"] = grouped["close"] / grouped["open"] - 1
    grouped["return_std"] = grouped["return_std"].fillna(0.0)
    return grouped
