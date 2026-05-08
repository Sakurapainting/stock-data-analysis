"""项目通用工具函数。"""

from __future__ import annotations

from pathlib import Path


def ensure_output_dirs(output_dir: Path) -> None:
    """创建输出目录结构。"""
    (output_dir / "data").mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)


def use_chinese_font_if_available() -> None:
    """优先设置常见中文字体，减少图表乱码。"""
    from matplotlib import font_manager
    import matplotlib.pyplot as plt

    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in candidates:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False
