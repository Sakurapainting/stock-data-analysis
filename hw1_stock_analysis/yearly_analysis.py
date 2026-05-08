"""年度分析与可视化。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.utils import ensure_output_dirs, use_chinese_font_if_available


@dataclass(frozen=True)
class YearlyAnalysisResult:
    """年度分析结果。"""

    yearly_df: pd.DataFrame
    annual_return_path: str
    cumulative_curve_path: str
    cumulative_return: float
    annualized_return: float


def analyze_yearly_data(daily_df: pd.DataFrame, config: RuntimeConfig) -> YearlyAnalysisResult:
    """分析 2018-2023 年年度收益率与波动率。"""
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("缺少 matplotlib，请先安装 requirements.txt 中的依赖。") from exc

    ensure_output_dirs(config.app.output_dir)
    use_chinese_font_if_available()

    yearly_df = daily_df[
        (daily_df["trade_date"] >= pd.Timestamp("2018-01-01"))
        & (daily_df["trade_date"] <= pd.Timestamp("2023-12-31"))
    ].copy()
    yearly_df["year"] = yearly_df["trade_date"].dt.year

    yearly_summary = yearly_df.groupby("year", as_index=False).agg(
        open=("open", "first"),
        close=("close", "last"),
        annual_volatility=("daily_return", lambda values: values.std() * np.sqrt(len(values))),
    )
    yearly_summary["annual_return"] = yearly_summary["close"] / yearly_summary["open"] - 1
    yearly_summary["annual_volatility"] = yearly_summary["annual_volatility"].fillna(0.0)

    full_period_days = max((yearly_df["trade_date"].max() - yearly_df["trade_date"].min()).days, 1)
    cumulative_return = yearly_df["close"].iloc[-1] / yearly_df["close"].iloc[0] - 1
    annualized_return = (1 + cumulative_return) ** (365.25 / full_period_days) - 1

    annual_return_path = config.app.output_dir / "figures" / "annual_return_bar.png"
    cumulative_curve_path = config.app.output_dir / "figures" / "cumulative_return_curve.png"
    _plot_annual_return(yearly_summary, annual_return_path, config.stock.ts_code)
    _plot_cumulative_curve(yearly_df, cumulative_curve_path, config.stock.ts_code)
    return YearlyAnalysisResult(
        yearly_df=yearly_summary,
        annual_return_path=str(annual_return_path),
        cumulative_curve_path=str(cumulative_curve_path),
        cumulative_return=float(cumulative_return),
        annualized_return=float(annualized_return),
    )


def _plot_annual_return(yearly_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """绘制年度收益率对比柱状图。"""
    import matplotlib.pyplot as plt

    colors = ["#d1495b" if value >= 0 else "#2d6a4f" for value in yearly_df["annual_return"]]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(yearly_df["year"].astype(str), yearly_df["annual_return"], color=colors)
    ax.set_title(f"{ts_code} 2018-2023 年度收益率对比")
    ax.set_xlabel("年份")
    ax.set_ylabel("年度收益率")
    ax.axhline(0, color="#333333", linewidth=1)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_cumulative_curve(yearly_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """绘制累计收益率曲线。"""
    import matplotlib.pyplot as plt

    curve_df = yearly_df.sort_values("trade_date").copy()
    curve_df["cumulative_return"] = (1 + curve_df["daily_return"]).cumprod() - 1
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(curve_df["trade_date"], curve_df["cumulative_return"], color="#1d3557", linewidth=2)
    ax.set_title(f"{ts_code} 2018-2023 累计收益率曲线")
    ax.set_xlabel("日期")
    ax.set_ylabel("累计收益率")
    ax.grid(alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
