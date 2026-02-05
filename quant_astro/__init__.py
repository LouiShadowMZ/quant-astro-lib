# quant_astro/__init__.py

# 核心计算逻辑
from .core import calculate_positions, decimal_to_dms, get_sun_rise_and_lord
from .points import calculate_special_points
from .kp import get_kp_lords, get_significators, get_ruling_planets

# <--- [新增] 导出相位计算
from .aspects import calculate_aspects 

# Dasha 运限系统
from .dasha_Vimshottari_api import create_dasha_table

# [新增] 图表与HTML生成 (取代了原来的 display 和 kp_api)
from .chart import generate_chart_html

# 定义包的版本信息 (建议升级版本号以标记架构变更)
__version__ = "0.1.5"