"""quant_astro 本地 Web 解耦计算接口（不包含服务端、Dasha 与庙旺落陷）。"""

from .core import (
    AstroContext,
    CHALDEAN_ORDER,
    HOUSE_SYSTEMS,
    MAIN_PLANETS,
    MINOR_PLANETS,
    WEEKDAY_LORDS,
    calculate_day_lord,
    calculate_fixed_stars,
    calculate_houses,
    calculate_minor_planets,
    calculate_planetary_hour,
    calculate_planets,
    calculate_sunrise_sunset,
    decimal_to_dms,
    parse_time_geo,
    set_ephemeris_path,
)
from .kp import (
    SignificatorMaps,
    build_significator_maps,
    calculate_house_significators,
    calculate_planet_significators,
    calculate_significators,
    get_horary_ascendant,
    get_kp_lords,
    get_ruling_planets,
    get_significators,
    kp_lookup,
    kp_lookup_many,
    load_kp_table,
    solve_horary_houses,  # 本体现在住在 kp.py（它依赖 KP 查表反推上升点）
)

# 注意：此前这里写的是 "0.2.1"，但 setup.py 里 version='0.1.8'，两处对不上。
# 这次顺带同步成一致的版本号，后续发布记得两边一起改。
__version__ = "0.2.2"

__all__ = [
    "AstroContext",
    "CHALDEAN_ORDER",
    "HOUSE_SYSTEMS",
    "MAIN_PLANETS",
    "MINOR_PLANETS",
    "WEEKDAY_LORDS",
    "SignificatorMaps",
    "build_significator_maps",
    "calculate_day_lord",
    "calculate_fixed_stars",
    "calculate_house_significators",
    "calculate_houses",
    "calculate_minor_planets",
    "calculate_planet_significators",
    "calculate_planetary_hour",
    "calculate_planets",
    "calculate_significators",
    "calculate_sunrise_sunset",
    "decimal_to_dms",
    "get_horary_ascendant",
    "get_kp_lords",
    "get_ruling_planets",
    "get_significators",
    "kp_lookup",
    "kp_lookup_many",
    "load_kp_table",
    "parse_time_geo",
    "set_ephemeris_path",
    "solve_horary_houses",
]
