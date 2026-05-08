"""月度分析与可视化。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.utils import ensure_output_dirs, use_chinese_font_if_available


@dataclass(frozen=True)
class MonthlyAnalysisResult:
    """月度分析结果。"""

    monthly_df: pd.DataFrame
    seasonal_return_df: pd.DataFrame
    close_line_path: str
    volume_heatmap_path: str
    best_month: str
    worst_month: str


def analyze_monthly_data(daily_df: pd.DataFrame, config: RuntimeConfig) -> MonthlyAnalysisResult:
    """分析最近三年的月度趋势、成交量与季节性。"""
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("缺少 matplotlib，请先安装 requirements.txt 中的依赖。") from exc

    ensure_output_dirs(config.app.output_dir)
    use_chinese_font_if_available()

    cutoff_date = daily_df["trade_date"].max() - pd.DateOffset(years=3)
    recent_df = daily_df[daily_df["trade_date"] >= cutoff_date].copy()
    recent_df["month_period"] = recent_df["trade_date"].dt.to_period("M")
    recent_df["year"] = recent_df["trade_date"].dt.year
    recent_df["month_num"] = recent_df["trade_date"].dt.month

    monthly_df = recent_df.groupby("month_period", as_index=False).agg(
        start_date=("trade_date", "min"),
        end_date=("trade_date", "max"),
        open=("open", "first"),
        close=("close", "last"),
        high=("high", "max"),
        low=("low", "min"),
        volume=("vol", "sum"),
    )
    monthly_df["month_num"] = monthly_df["month_period"].map(lambda period: period.month)
    monthly_df["month_period"] = monthly_df["month_period"].astype(str)
    monthly_df["monthly_return"] = monthly_df["close"] / monthly_df["open"] - 1

    seasonal_return_df = monthly_df.groupby("month_num", as_index=False).agg(
        avg_monthly_return=("monthly_return", "mean"),
    )
    seasonal_return_df["month_label"] = seasonal_return_df["month_num"].map(
        lambda value: f"{value}月"
    )
    best_row = seasonal_return_df.loc[seasonal_return_df["avg_monthly_return"].idxmax()]
    worst_row = seasonal_return_df.loc[seasonal_return_df["avg_monthly_return"].idxmin()]

    close_line_path = config.app.output_dir / "figures" / "monthly_close_line.png"
    volume_heatmap_path = config.app.output_dir / "figures" / "monthly_volume_heatmap.png"
    _plot_monthly_close(monthly_df, close_line_path, config.stock.ts_code)
    _plot_volume_heatmap(recent_df, volume_heatmap_path, config.stock.ts_code)
    return MonthlyAnalysisResult(
        monthly_df=monthly_df,
        seasonal_return_df=seasonal_return_df,
        close_line_path=str(close_line_path),
        volume_heatmap_path=str(volume_heatmap_path),
        best_month=str(best_row["month_label"]),
        worst_month=str(worst_row["month_label"]),
    )


def _plot_monthly_close(monthly_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """绘制月度收盘价折线图。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        monthly_df["month_period"],
        monthly_df["close"],
        color="#1d3557",
        marker="o",
        linewidth=2,
    )
    ax.set_title(f"{ts_code} 最近三年月度收盘价趋势")
    ax.set_xlabel("月份")
    ax.set_ylabel("收盘价")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_volume_heatmap(recent_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """绘制按年-月组织的成交量热力图。"""
    import matplotlib.pyplot as plt

    pivot = recent_df.pivot_table(
        index="year",
        columns="month_num",
        values="vol",
        aggfunc="sum",
        fill_value=0.0,
    )
    month_columns = list(range(1, 13))
    pivot = pivot.reindex(columns=month_columns, fill_value=0.0)

    fig, ax = plt.subplots(figsize=(12, 6))
    image = ax.imshow(pivot.values, cmap="YlOrBr", aspect="auto")
    ax.set_title(f"{ts_code} 最近三年月度成交量热力图")
    ax.set_xlabel("月份")
    ax.set_ylabel("年份")
    ax.set_xticks(np.arange(len(month_columns)))
    ax.set_xticklabels([f"{item}月" for item in month_columns])
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index.astype(str).tolist())
    fig.colorbar(image, ax=ax, label="成交量")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
