"""检查 Tushare token、积分和 daily 接口权限。"""

from __future__ import annotations

from pathlib import Path

from hw1_stock_analysis.config_loader import load_config, validate_runtime_config
from hw1_stock_analysis.fetch_store import TushareAccessError, _get_tushare_pro


def main() -> None:
    """输出当前 token 的账户和接口权限状态。"""
    config = load_config(Path("config.ini"))
    validate_runtime_config(config)
    pro = _get_tushare_pro(config.tushare_token)

    print("1. 查询账户积分到期信息")
    try:
        user_df = pro.user(token=config.tushare_token)
        if user_df.empty:
            print("未查询到积分记录，请登录 Tushare 官网个人主页再次确认。")
        else:
            print(user_df.to_string(index=False))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"查询积分信息失败：{exc}")

    print("\n2. 测试 daily 接口权限")
    try:
        test_df = pro.daily(ts_code=config.stock.ts_code, start_date="20231201", end_date="20231231")
        print(f"daily 接口可用，返回 {len(test_df)} 条记录。")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise TushareAccessError(str(exc)) from exc


if __name__ == "__main__":
    main()
