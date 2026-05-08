"""周度分析与可视化。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.utils import ensure_output_dirs, use_chinese_font_if_available


@dataclass(frozen=True)
class WeeklyAnalysisResult:
    """周度分析结果。"""

    weekly_df: pd.DataFrame
    top_volatility_weeks: pd.DataFrame
    candlestick_path: str
    return_bar_path: str


def analyze_weekly_data(daily_df: pd.DataFrame, config: RuntimeConfig) -> WeeklyAnalysisResult:
    """统计最近一年的周线特征并生成图表。"""
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("缺少 matplotlib，请先安装 requirements.txt 中的依赖。") from exc

    ensure_output_dirs(config.app.output_dir)
    use_chinese_font_if_available()

    cutoff_date = daily_df["trade_date"].max() - pd.Timedelta(days=365)
    recent_df = daily_df[daily_df["trade_date"] >= cutoff_date].copy()
    recent_df["week"] = recent_df["trade_date"].dt.to_period("W")

    weekly_df = recent_df.groupby("week", as_index=False).agg(
        start_date=("trade_date", "min"),
        end_date=("trade_date", "max"),
        open=("open", "first"),
        close=("close", "last"),
        high=("high", "max"),
        low=("low", "min"),
        volume=("vol", "sum"),
    )
    weekly_df["week"] = weekly_df["week"].astype(str)
    weekly_df["weekly_return"] = weekly_df["close"] / weekly_df["open"] - 1
    weekly_df["range_ratio"] = (weekly_df["high"] - weekly_df["low"]) / weekly_df["open"]
    top3 = weekly_df.nlargest(3, "range_ratio")[["week", "range_ratio", "weekly_return"]].copy()

    candlestick_path = config.app.output_dir / "figures" / "weekly_candlestick.png"
    return_bar_path = config.app.output_dir / "figures" / "weekly_return_bar.png"
    _plot_weekly_candlestick(weekly_df, candlestick_path, config.stock.ts_code)
    _plot_weekly_returns(weekly_df, return_bar_path, config.stock.ts_code)
    return WeeklyAnalysisResult(
        weekly_df=weekly_df,
        top_volatility_weeks=top3,
        candlestick_path=str(candlestick_path),
        return_bar_path=str(return_bar_path),
    )


def _plot_weekly_candlestick(weekly_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """使用 Matplotlib 原生图元绘制简化周 K 线。"""
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 7))
    x_positions = range(len(weekly_df))
    for idx, row in enumerate(weekly_df.itertuples(index=False)):
        color = "#d1495b" if row.close >= row.open else "#2d6a4f"
        ax.plot([idx, idx], [row.low, row.high], color=color, linewidth=1.4)
        rect_bottom = min(row.open, row.close)
        rect_height = max(abs(row.close - row.open), 0.01)
        candle = patches.Rectangle(
            (idx - 0.3, rect_bottom),
            0.6,
            rect_height,
            facecolor=color,
            edgecolor=color,
            alpha=0.8,
        )
        ax.add_patch(candle)

    tick_step = max(1, len(weekly_df) // 10)
    ax.set_xticks(list(x_positions)[::tick_step])
    ax.set_xticklabels(weekly_df["week"].tolist()[::tick_step], rotation=45, ha="right")
    ax.set_title(f"{ts_code} 最近一年周K线图")
    ax.set_xlabel("交易周")
    ax.set_ylabel("价格")
    ax.grid(alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_weekly_returns(weekly_df: pd.DataFrame, output_path, ts_code: str) -> None:
    """绘制周收益率柱状图。"""
    import matplotlib.pyplot as plt

    colors = ["#d1495b" if value >= 0 else "#2d6a4f" for value in weekly_df["weekly_return"]]
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(weekly_df["week"], weekly_df["weekly_return"], color=colors)
    ax.set_title(f"{ts_code} 最近一年周收益率")
    ax.set_xlabel("交易周")
    ax.set_ylabel("收益率")
    ax.tick_params(axis="x", rotation=45)
    ax.axhline(0, color="#333333", linewidth=1)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
