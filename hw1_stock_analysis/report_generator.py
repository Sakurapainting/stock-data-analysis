"""综合分析报告生成模块。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hw1_stock_analysis.config_loader import RuntimeConfig
from hw1_stock_analysis.monthly_analysis import MonthlyAnalysisResult
from hw1_stock_analysis.preprocess import ProcessedData
from hw1_stock_analysis.weekly_analysis import WeeklyAnalysisResult
from hw1_stock_analysis.yearly_analysis import YearlyAnalysisResult


def generate_markdown_report(
    config: RuntimeConfig,
    processed: ProcessedData,
    weekly_result: WeeklyAnalysisResult,
    monthly_result: MonthlyAnalysisResult,
    yearly_result: YearlyAnalysisResult,
) -> Path:
    """将分析结果汇总成 Markdown 报告。"""
    report_path = config.app.output_dir / "report.md"
    weekly_mean = weekly_result.weekly_df["weekly_return"].mean()
    weekly_std = weekly_result.weekly_df["weekly_return"].std()
    volume_mean = processed.daily["vol"].mean()
    price_span = processed.daily["close"].max() - processed.daily["close"].min()

    top3_lines = "\n".join(
        f"- {row.week}：波动幅度 {row.range_ratio:.2%}，周收益率 {row.weekly_return:.2%}"
        for row in weekly_result.top_volatility_weeks.itertuples(index=False)
    )
    annual_table = _build_markdown_table(yearly_result.yearly_df)

    content = f"""# 股票数据分析报告

## 1. 基本信息
- 股票代码：{config.stock.ts_code}
- 股票名称：{config.stock.stock_name or "待补充"}
- 数据区间：{config.app.start_date} - {config.app.end_date}
- 日线记录数：{len(processed.daily)}

## 2. 数据预处理结论
- 通过插值、前向填充和后向填充处理了缺失值，避免关键价格字段为空。
- 对开盘价、最高价、最低价、收盘价、成交量和成交额做了 1% - 99% 分位数裁剪，用于减弱极端异常值影响。
- 新增了 `daily_return`、`ma5` 和 `volume_volatility` 三个衍生指标，并同步输出周、月、年三级聚合 CSV。

## 3. 周度分析
- 最近一年平均周收益率：{weekly_mean:.2%}
- 最近一年周收益率标准差：{0.0 if pd.isna(weekly_std) else weekly_std:.2%}
- 价格振幅最大的 3 个交易周：
{top3_lines}

![周K线图](figures/weekly_candlestick.png)

![周收益率柱状图](figures/weekly_return_bar.png)

## 4. 月度分析
- 最近三年平均日成交量：{volume_mean:.2f}
- 季节性表现最佳月份：{monthly_result.best_month}
- 季节性表现最弱月份：{monthly_result.worst_month}

![月度收盘价折线图](figures/monthly_close_line.png)

![月度成交量热力图](figures/monthly_volume_heatmap.png)

## 5. 年度分析
- 2018-2023 样本区间累计收益率：{yearly_result.cumulative_return:.2%}
- 2018-2023 样本区间年化收益率：{yearly_result.annualized_return:.2%}
- 区间价格跨度：{price_span:.2f}

{annual_table}

![年度收益率柱状图](figures/annual_return_bar.png)

![累计收益率曲线图](figures/cumulative_return_curve.png)

## 6. 综合结论
1. 从周度数据看，该股票短周期收益率存在明显波动，适合结合风险偏好进行节奏控制。
2. 从月度季节性看，不同月份的收益表现差异较大，说明时间窗口对交易结果有显著影响。
3. 从年度趋势看，长期收益能力与年度波动率需要同时考察，不能仅凭单一年度涨跌下结论。

## 7. 投资建议
1. 若周收益率波动明显偏大，可采用分批建仓方式控制一次性买入风险。
2. 若历史上某些月份平均收益较弱，可在这些月份适当降低仓位或提高止损敏感度。
3. 若年度波动率上升但累计收益率没有同步改善，应优先考虑风险收益比，而不是只看绝对涨幅。

## 8. 说明
- 大盘指数相关性分析为选做项，当前版本未默认开启。
- 若你在实际运行后补充了股票名称、最终图表和口头分析，可直接将本报告作为提交材料的一部分。
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def _build_markdown_table(dataframe) -> str:
    """手动构造 Markdown 表格，避免额外依赖 tabulate。"""
    headers = list(dataframe.columns)
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = []
    for row in dataframe.itertuples(index=False):
        formatted = []
        for value in row:
            if isinstance(value, float):
                formatted.append(f"{value:.6f}")
            else:
                formatted.append(str(value))
        row_lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join([header_line, separator_line, *row_lines])
