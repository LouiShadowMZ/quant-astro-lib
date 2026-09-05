# quant_astro/__init__.py

# 核心计算逻辑
from .core import calculate_positions, decimal_to_dms, calculate_fixed_stars, get_sun_rise_and_lord, get_planetary_hour
from .attributes import get_attributes
from .points import calculate_special_points
from .kp import get_kp_lords, get_significators, get_ruling_planets

# <--- [新增] 导出相位计算
from .aspects import calculate_aspects 

# Dasha 运限系统
from .dasha_Vimshottari_api import create_dasha_table

# [新增] 图表与HTML生成 (取代了原来的 display 和 kp_api)
from .chart import generate_chart_html

# 定义包的版本信息 (建议升级版本号以标记架构变更)
# 0.1.7: 补全 house_codes 缺失的 5 种宫位制；统一 core.py 两处岁差(ayanamsha)名称解析逻辑
#        （修复 calculate_fixed_stars 在非法/非字符串岁差名称时静默不调用 set_sid_mode 的问题）；
#        sub-sub.csv 查找表改为进程内缓存，避免每次算盘重复读盘解析。大运(dasha)相关代码未改动。
__version__ = "0.1.7"