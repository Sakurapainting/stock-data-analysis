"""读取与校验运行配置。"""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from hw1_stock_analysis.stock_code import build_stock_code


PLACEHOLDER_PREFIX = "REPLACE_WITH_"


@dataclass(frozen=True)
class MysqlConfig:
    """MySQL 连接配置。"""

    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str


@dataclass(frozen=True)
class StockConfig:
    """股票与学号配置。"""

    student_id: str
    market: str
    ts_code: str
    stock_name: str


@dataclass(frozen=True)
class AppConfig:
    """应用级配置。"""

    start_date: str
    end_date: str
    output_dir: Path


@dataclass(frozen=True)
class RuntimeConfig:
    """程序总配置。"""

    tushare_token: str
    mysql: MysqlConfig
    stock: StockConfig
    app: AppConfig


def load_config(config_path: Path) -> RuntimeConfig:
    """从 INI 文件中读取配置。"""
    if not config_path.exists():
        raise FileNotFoundError(
            f"未找到配置文件：{config_path}。请先复制 config.ini.example 为 config.ini。"
        )

    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")

    ts_code_override = parser.get("stock", "ts_code_override", fallback="").strip()
    student_id = parser.get("stock", "student_id").strip()
    market = parser.get("stock", "market").strip()
    if ts_code_override:
        ts_code = ts_code_override
    elif student_id and not student_id.startswith(PLACEHOLDER_PREFIX):
        ts_code = build_stock_code(student_id, market)
    else:
        ts_code = ""

    output_dir = Path(parser.get("app", "output_dir", fallback="output")).resolve()
    return RuntimeConfig(
        tushare_token=parser.get("tushare", "token").strip(),
        mysql=MysqlConfig(
            host=parser.get("mysql", "host").strip(),
            port=parser.getint("mysql", "port"),
            user=parser.get("mysql", "user").strip(),
            password=parser.get("mysql", "password").strip(),
            database=parser.get("mysql", "database").strip(),
            charset=parser.get("mysql", "charset", fallback="utf8mb4").strip(),
        ),
        stock=StockConfig(
            student_id=student_id,
            market=market,
            ts_code=ts_code,
            stock_name=parser.get("stock", "stock_name", fallback="").strip(),
        ),
        app=AppConfig(
            start_date=parser.get("app", "start_date").strip(),
            end_date=parser.get("app", "end_date").strip(),
            output_dir=output_dir,
        ),
    )


def validate_runtime_config(config: RuntimeConfig) -> None:
    """校验运行前必须填写的配置项。"""
    invalid_fields = []
    values = {
        "tushare.token": config.tushare_token,
        "mysql.password": config.mysql.password,
        "stock.student_id": config.stock.student_id,
    }
    for field_name, value in values.items():
        if not value or value.startswith(PLACEHOLDER_PREFIX):
            invalid_fields.append(field_name)

    if invalid_fields:
        joined = ", ".join(invalid_fields)
        raise ValueError(f"以下配置仍是占位值，请先填写后再运行：{joined}")
