# quant_astro/__init__.py

# 核心计算逻辑
from .core import calculate_positions, decimal_to_dms, calculate_fixed_stars, get_sun_rise_and_lord, get_planetary_hour
from .kp import get_kp_lords, get_significators, get_ruling_planets

# Dasha 运限系统
from .dasha_Vimshottari_api import create_dasha_table

# 定义包的版本信息 (建议升级版本号以标记架构变更)
# 0.1.7: 补全 house_codes 缺失的 5 种宫位制；统一 core.py 两处岁差(ayanamsha)名称解析逻辑
#        （修复 calculate_fixed_stars 在非法/非字符串岁差名称时静默不调用 set_sid_mode 的问题）；
#        sub-sub.csv 查找表改为进程内缓存，避免每次算盘重复读盘解析。大运(dasha)相关代码未改动。
# 0.1.8: 修复 swe.cotrans 黄道->赤道换算符号错误（房宫头/南交点 Ke 的 ra/dec 此前因传入
#        +eps 而非 -eps 而算错，经纬度/星座/星主等主计算不受影响）；修复 _parse_timezone
#        无法解析 '+5.5' 这类小数小时格式而崩溃(AttributeError)的问题；简化 fixstar2_ut /
#        rise_trans 处几处永远走不到的返回值猜测分支，及冗余的 except (swe.Error, Exception)。
#        本次改动同步更新了 setup.py 的 version，避免两处版本号不一致。
__version__ = "0.1.8"