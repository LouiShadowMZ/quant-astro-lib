# quant_astro/__init__.py

# 让用户可以直接从 quant_astro 导入这些核心函数
from .core import calculate_positions
from .points import calculate_special_points
from .kp import get_kp_lords
from .display import display_kp_table

# 定义包的版本信息
__version__ = "0.1.0"