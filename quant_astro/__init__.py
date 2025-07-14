# quant_astro/__init__.py

# 让用户可以直接从 quant_astro 导入这些核心函数
from .core import calculate_positions
from .points import calculate_special_points
from .kp import get_kp_lords
from .display import display_kp_table

# 核心修改：从 api.py 导入我们新创建的一键调用函数

from .dasha_Vimshottari_api import create_dasha_table

# 定义包的版本信息
__version__ = "0.2.0"