"""MySQL 数据库操作模块。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Iterable

import pandas as pd

from hw1_stock_analysis.config_loader import MysqlConfig


class DatabaseConnectionError(RuntimeError):
    """数据库连接异常。"""


class DatabaseClient:
    """封装数据库初始化、查询与增量写入操作。"""

    def __init__(self, config: MysqlConfig) -> None:
        self.config = config

    def _connect(self, with_database: bool = True):
        """创建数据库连接。"""
        try:
            import pymysql
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("缺少 PyMySQL，请先安装 requirements.txt 中的依赖。") from exc

        kwargs = asdict(self.config)
        if not with_database:
            kwargs.pop("database")
        try:
            return pymysql.connect(
                **kwargs,
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor,
            )
        except pymysql.err.OperationalError as exc:
            raise DatabaseConnectionError(self._build_connection_error_message(exc)) from exc
        except RuntimeError as exc:
            raise DatabaseConnectionError(self._build_runtime_dependency_message(exc)) from exc

    def _build_connection_error_message(self, exc: Exception) -> str:
        """构造更易懂的数据库连接报错信息。"""
        return (
            "无法连接到 MySQL。\n"
            f"当前配置：host={self.config.host}, port={self.config.port}, user={self.config.user}, "
            f"database={self.config.database}\n"
            "请优先检查以下几项：\n"
            "1. MySQL 服务是否已经启动。\n"
            "2. config.ini 中的 host / port 是否与本机 MySQL 实际配置一致。\n"
            "3. root 用户和密码是否正确，并且允许本机连接。\n"
            "4. 如果你安装的是 MySQL80，Windows 服务里应看到 MySQL80 处于 Running。\n"
            f"原始错误：{exc}"
        )

    def _build_runtime_dependency_message(self, exc: Exception) -> str:
        """构造运行时依赖缺失提示。"""
        return (
            "MySQL 已经可以连接，但当前认证方式需要额外的 Python 依赖。\n"
            "请在作业环境中安装 `cryptography` 后重试：\n"
            "conda run -n iot_hw1 python -m pip install cryptography\n"
            f"原始错误：{exc}"
        )

    def initialize(self) -> None:
        """初始化数据库与数据表。"""
        create_database_sql = (
            f"CREATE DATABASE IF NOT EXISTS `{self.config.database}` "
            f"DEFAULT CHARACTER SET {self.config.charset}"
        )
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_daily (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            ts_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            open_price DECIMAL(12, 4),
            high_price DECIMAL(12, 4),
            low_price DECIMAL(12, 4),
            close_price DECIMAL(12, 4),
            pre_close DECIMAL(12, 4),
            price_change DECIMAL(12, 4),
            pct_chg DECIMAL(12, 4),
            vol DECIMAL(20, 4),
            amount DECIMAL(20, 4),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            UNIQUE KEY uk_ts_code_trade_date (ts_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        with self._connect(with_database=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(create_database_sql)
            connection.commit()

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(create_table_sql)
            connection.commit()

    def get_latest_trade_date(self, ts_code: str) -> str | None:
        """查询某支股票已存储的最新交易日。"""
        sql = """
        SELECT DATE_FORMAT(MAX(trade_date), '%%Y%%m%%d') AS latest_trade_date
        FROM stock_daily
        WHERE ts_code = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (ts_code,))
                row = cursor.fetchone()
        return row["latest_trade_date"] if row and row["latest_trade_date"] else None

    def upsert_daily_rows(self, rows: Iterable[tuple]) -> int:
        """使用唯一键实现日线数据增量更新。"""
        sql = """
        INSERT INTO stock_daily (
            ts_code, trade_date, open_price, high_price, low_price, close_price,
            pre_close, price_change, pct_chg, vol, amount, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            open_price = VALUES(open_price),
            high_price = VALUES(high_price),
            low_price = VALUES(low_price),
            close_price = VALUES(close_price),
            pre_close = VALUES(pre_close),
            price_change = VALUES(price_change),
            pct_chg = VALUES(pct_chg),
            vol = VALUES(vol),
            amount = VALUES(amount),
            updated_at = VALUES(updated_at)
        """
        row_list = list(rows)
        if not row_list:
            return 0

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(sql, row_list)
            connection.commit()
        return len(row_list)

    def load_daily_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """按时间范围从数据库读取日线数据。"""
        sql = """
        SELECT
            ts_code,
            trade_date,
            open_price AS open,
            high_price AS high,
            low_price AS low,
            close_price AS close,
            pre_close,
            price_change AS `change`,
            pct_chg,
            vol,
            amount
        FROM stock_daily
        WHERE ts_code = %s AND trade_date BETWEEN %s AND %s
        ORDER BY trade_date ASC
        """
        params = (
            ts_code,
            datetime.strptime(start_date, "%Y%m%d").date(),
            datetime.strptime(end_date, "%Y%m%d").date(),
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            df = pd.DataFrame(rows)
        return df


def load_daily_data(
    db_client: DatabaseClient,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """对外暴露的日线数据读取函数。"""
    return db_client.load_daily_data(ts_code, start_date, end_date)
