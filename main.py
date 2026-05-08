"""作业一主程序入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from hw1_stock_analysis.config_loader import load_config, validate_runtime_config
from hw1_stock_analysis.db import DatabaseClient, load_daily_data
from hw1_stock_analysis.fetch_store import fetch_and_store_daily_data
from hw1_stock_analysis.monthly_analysis import analyze_monthly_data
from hw1_stock_analysis.preprocess import preprocess_daily_data
from hw1_stock_analysis.report_generator import generate_markdown_report
from hw1_stock_analysis.weekly_analysis import analyze_weekly_data
from hw1_stock_analysis.yearly_analysis import analyze_yearly_data


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="股票数据分析作业一")
    parser.add_argument(
        "--config",
        default="config.ini",
        help="配置文件路径，默认读取当前目录下的 config.ini",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="跳过 Tushare 拉取步骤，直接从 MySQL 中读取已有数据。",
    )
    return parser.parse_args()


def main() -> None:
    """串联作业要求的完整处理流程。"""
    args = parse_args()
    config = load_config(Path(args.config))
    validate_runtime_config(config)

    db_client = DatabaseClient(config.mysql)
    db_client.initialize()

    if not args.skip_fetch:
        fetch_and_store_daily_data(config, db_client)

    daily_df = load_daily_data(
        db_client,
        config.stock.ts_code,
        config.app.start_date,
        config.app.end_date,
    )
    processed = preprocess_daily_data(daily_df, config)

    weekly_result = analyze_weekly_data(processed.daily, config)
    monthly_result = analyze_monthly_data(processed.daily, config)
    yearly_result = analyze_yearly_data(processed.daily, config)

    report_path = generate_markdown_report(
        config=config,
        processed=processed,
        weekly_result=weekly_result,
        monthly_result=monthly_result,
        yearly_result=yearly_result,
    )

    print(f"分析完成，报告已生成：{report_path}")


if __name__ == "__main__":
    main()
