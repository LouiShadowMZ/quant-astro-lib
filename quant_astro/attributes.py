# quant_astro/attributes.py

import swisseph as swe

# 从 core.py 借入这两个函数，这样 __init__.py 不需要改动
from .core import get_sun_rise_and_lord, get_planetary_hour

# --- 常量定义 ---
ZODIAC_NAMES = ['Ari', 'Tau', 'Gem', 'Cnc', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqr', 'Pis']

# 古典占星/KP/吠陀占星 守护星映射 (Traditional Rulership)
SIGN_LORDS_MAP = {
    0: 'Ma', 1: 'Ve', 2: 'Me', 3: 'Mo', 4: 'Su', 5: 'Me',
    6: 'Ve', 7: 'Ma', 8: 'Ju', 9: 'Sa', 10: 'Sa', 11: 'Ju'
}

# --- 埃及界与托勒密界边界定义 ---
# 格式：[(限制度数, 星体简写), ...]，度数在区间 [前一个限制度数, 当前限制度数) 之间归属于该星体
EGYPTIAN_BOUNDS = {
    0:  [(6, 'Ju'), (12, 'Ve'), (20, 'Me'), (25, 'Ma'), (30, 'Sa')],  # Aries
    1:  [(8, 'Ve'), (14, 'Me'), (22, 'Ju'), (27, 'Sa'), (30, 'Ma')],  # Taurus
    2:  [(6, 'Me'), (12, 'Ju'), (17, 'Ve'), (24, 'Ma'), (30, 'Sa')],  # Gemini
    3:  [(7, 'Ma'), (13, 'Ve'), (19, 'Me'), (26, 'Ju'), (30, 'Sa')],  # Cancer
    4:  [(6, 'Ju'), (11, 'Ve'), (18, 'Sa'), (24, 'Me'), (30, 'Ma')],  # Leo
    5:  [(7, 'Me'), (17, 'Ve'), (21, 'Ju'), (28, 'Ma'), (30, 'Sa')],  # Virgo
    6:  [(6, 'Sa'), (14, 'Me'), (21, 'Ju'), (28, 'Ve'), (30, 'Ma')],  # Libra
    7:  [(7, 'Ma'), (11, 'Ve'), (19, 'Me'), (24, 'Ju'), (30, 'Sa')],  # Scorpio
    8:  [(12, 'Ju'), (17, 'Ve'), (21, 'Me'), (26, 'Sa'), (30, 'Ma')], # Sagittarius
    9:  [(7, 'Me'), (14, 'Ju'), (22, 'Ve'), (26, 'Sa'), (30, 'Ma')],  # Capricorn
    10: [(7, 'Me'), (12, 'Ve'), (20, 'Ju'), (25, 'Ma'), (30, 'Sa')],  # Aquarius
    11: [(12, 'Ve'), (16, 'Ju'), (19, 'Me'), (28, 'Ma'), (30, 'Sa')], # Pisces
}

PTOLEMAIC_BOUNDS = {
    0:  [(6, 'Ju'), (14, 'Ve'), (21, 'Me'), (26, 'Ma'), (30, 'Sa')],  # Aries
    1:  [(8, 'Ve'), (15, 'Me'), (22, 'Ju'), (26, 'Sa'), (30, 'Ma')],  # Taurus
    2:  [(7, 'Me'), (14, 'Ju'), (21, 'Ve'), (25, 'Sa'), (30, 'Ma')],  # Gemini
    3:  [(6, 'Ma'), (13, 'Ju'), (20, 'Me'), (27, 'Ve'), (30, 'Sa')],  # Cancer
    4:  [(6, 'Sa'), (13, 'Me'), (19, 'Ve'), (25, 'Ju'), (30, 'Ma')],  # Leo
    5:  [(7, 'Me'), (13, 'Ve'), (18, 'Ju'), (24, 'Sa'), (30, 'Ma')],  # Virgo
    6:  [(6, 'Sa'), (11, 'Ve'), (19, 'Ju'), (24, 'Me'), (30, 'Ma')],  # Libra
    7:  [(6, 'Ma'), (14, 'Ju'), (21, 'Ve'), (27, 'Me'), (30, 'Sa')],  # Scorpio
    8:  [(8, 'Ju'), (14, 'Ve'), (19, 'Me'), (25, 'Sa'), (30, 'Ma')],  # Sagittarius
    9:  [(6, 'Ve'), (12, 'Me'), (19, 'Ju'), (25, 'Ma'), (30, 'Sa')],  # Capricorn
    10: [(6, 'Sa'), (12, 'Me'), (20, 'Ve'), (25, 'Ju'), (30, 'Ma')],  # Aquarius
    11: [(8, 'Ve'), (14, 'Ju'), (20, 'Me'), (26, 'Ma'), (30, 'Sa')],  # Pisces
}

# --- 阿拉伯点计算规则 (昼夜公式映射) ---
# 通用公式：lot = ASC + A - B
# day/night 元组：(A, B)
# [修改] 已去掉所有 "Lot of " 前缀，键名直接使用点名本身
LOT_RULES = {
    "Fortune": {
        "day":   ("Mo", "Su"),
        "night": ("Su", "Mo"),
    },
    "Spirit": {
        "day":   ("Su", "Mo"),
        "night": ("Mo", "Su"),
    },
    "Necessity": {
        "day":   ("Fortune", "Spirit"),
        "night": ("Spirit", "Fortune"),
    },
    "Eros": {
        "day":   ("Spirit", "Fortune"),
        "night": ("Fortune", "Spirit"),
    },
    "Courage": {
        "day":   ("Fortune", "Ma"),
        "night": ("Ma", "Fortune"),
    },
    "Victory": {
        "day":   ("Ju", "Spirit"),
        "night": ("Spirit", "Ju"),
    },
    "Nemesis": {
        "day":   ("Fortune", "Sa"),
        "night": ("Sa", "Fortune"),
    },
    "the Father": {
        "day":   ("Sa", "Su"),
        "night": ("Su", "Sa"),
    },
    "the Mother": {
        "day":   ("Mo", "Ve"),
        "night": ("Ve", "Mo"),
    },
    "Siblings": {
        "day":   ("Ju", "Sa"),
        "night": ("Sa", "Ju"),
    },
    "Children": {
        "day":   ("Sa", "Ju"),
        "night": ("Ju", "Sa"),
    },
    "Marriage": {
        "day":   ("Ve", "Ju"),
        "night": ("Ju", "Ve"),
    },
    "Exaltation": {
        # 昼：ASC + 19°(太阳旺位·白羊19°) - 太阳
        # 夜：ASC + 33°(月亮旺位·金牛3°)  - 月亮
        "day":   ("const_19", "Su"),
        "night": ("const_33", "Mo"),
    },
    "Basis": {
        # 需要特殊计算逻辑，见下方 special == "basis" 分支
        "special": "basis",
    },
    "Debt": {
        "day":   ("Sa", "Me"),
        "night": ("Me", "Sa"),
    },
    "Chronic Illness": {
        "day":   ("Ma", "Sa"),
        "night": ("Sa", "Ma"),
    },
    "Death": {
        "day":   ("house 8", "Mo"),
        "night": ("Mo", "house 8"),
    },
}


# =============================================================================
# 辅助函数
# =============================================================================

def get_bound_planet(sign_idx, deg_in_sign, system="Egyptian"):
    """获取星座特定度数处的界（Bounds）主宰星"""
    bounds_table = EGYPTIAN_BOUNDS if system == "Egyptian" else PTOLEMAIC_BOUNDS
    sign_bounds = bounds_table.get(sign_idx, [])
    for limit, planet in sign_bounds:
        if deg_in_sign < limit:
            return planet
    return "Unknown"


def is_below_horizon(p_lon, asc_lon):
    """
    判断黄经点是否在地平线以下（即 Houses 1 至 6 区间，从 ASC 顺时针到 DSC）。
    """
    dsc_lon = (asc_lon + 180.0) % 360.0
    if dsc_lon < asc_lon:          # DSC 跨越 0° 的情况
        return p_lon >= asc_lon or p_lon < dsc_lon
    else:
        return asc_lon <= p_lon < dsc_lon


def build_celestial_dict(lon, lat, speed, eps, bounds_system="Egyptian"):
    """
    通用构建高精度星体字典函数。
    将黄道坐标转换为赤道坐标，并同时计算界（Bound）和面（Face）。

    参数：
        lon          : 黄经（度，0-360）
        lat          : 黄纬（度）
        speed        : 黄经日速度（度/天）
        eps          : 真实黄赤交角（由 swe.calc_ut(jd, ECL_NUT) 获取）
        bounds_system: 界体系，"Egyptian" 或 "Ptolemaic"
    """
    lon = lon % 360.0

    # 黄道 → 赤道高精度转换（含速度分量）
    # 输入格式：(lon, lat, dist, speed_lon, speed_lat, speed_dist)
    # eps 为正值 = 黄道坐标 → 赤道坐标（ecliptic to equatorial）
    xpo = (lon, lat, 1.0, speed, 0.0, 0.0)
    res = swe.cotrans_sp(xpo, eps)

    ra       = res[0] % 360.0
    dec      = res[1]
    dec_speed = res[4]

    sign_idx    = int(lon / 30.0) % 12
    deg_in_sign = lon % 30.0

    # 界 (Bound)
    bound_planet = get_bound_planet(sign_idx, deg_in_sign, system=bounds_system)

    # 面 (Face) — 迦勒底序列，每 10 度一面
    face_idx = min(int(deg_in_sign / 10.0), 2)
    total_decan = sign_idx * 3 + face_idx
    chaldean_order = ['Ma', 'Su', 'Ve', 'Me', 'Mo', 'Sa', 'Ju']
    face_planet = chaldean_order[total_decan % 7]

    return {
        'lon':       lon,
        'lat':       lat,
        'speed':     speed,
        'ra':        ra,
        'dec':       dec,
        'dec_speed': dec_speed,
        'bound':     bound_planet,
        'face':      face_planet,
    }


def add_bounds_and_faces(pos_dict, bounds_system="Egyptian"):
    """
    为已有星体字典（行星/宫位/小行星/恒星）追加界（bound）和面（face）参数。
    只读取 'lon' 字段，不修改其他字段。
    """
    new_dict = {}
    for key, val in pos_dict.items():
        copied = val.copy()
        lon = copied['lon']
        sign_idx    = int(lon / 30.0) % 12
        deg_in_sign = lon % 30.0

        # 界
        bound_planet = get_bound_planet(sign_idx, deg_in_sign, system=bounds_system)

        # 面
        face_idx = min(int(deg_in_sign / 10.0), 2)
        total_decan = sign_idx * 3 + face_idx
        chaldean_order = ['Ma', 'Su', 'Ve', 'Me', 'Mo', 'Sa', 'Ju']
        face_planet = chaldean_order[total_decan % 7]

        copied['bound'] = bound_planet
        copied['face']  = face_planet
        new_dict[key]   = copied
    return new_dict


def get_lon_speed(body, planet_positions, house_positions, temp_lots=None):
    """
    安全提取任意星体的黄经度数与速度。
    查找顺序：Asc → 宫头 → 已算阿拉伯点 → 行星。
    找不到时返回 (None, None)，调用方负责跳过。
    """
    if body == 'Asc':
        if 'house 1' in house_positions:
            h = house_positions['house 1']
            return h['lon'], h['speed']
    elif body.startswith('house '):
        if body in house_positions:
            h = house_positions[body]
            return h['lon'], h['speed']
    elif temp_lots and body in temp_lots:
        t = temp_lots[body]
        return t['lon'], t['speed']
    else:
        if body in planet_positions:
            p = planet_positions[body]
            return p['lon'], p['speed']
    return None, None


# =============================================================================
# 主入口函数
# =============================================================================

def get_attributes(
    planet_positions,
    house_positions,
    jd=None,
    selected_lots="all",
    lot_method="sect",
    bounds_system="Egyptian",
    minor_planet_positions=None,
    fixed_star_positions=None,
    **kwargs
):
    """
    attributes.py 核心入口。

    计算内容：
        · 阿拉伯点（Paulus of Alexandria 体系，共 17 个，支持日夜区分）
        · 映点（Antiscia）与反映点（Contra-Antiscia）
        · 所有星体的界（Bound）与面（Face）

    参数：
        planet_positions       : core.py 返回的主行星字典
        house_positions        : core.py 返回的宫头字典
        jd                     : 儒略日（用于精确计算黄赤交角，强烈建议传入）
        selected_lots          : 选择输出哪些阿拉伯点
                                 "all" = 全部；或传列表，如 ["Fortune", "Spirit"]
        lot_method             : 日夜判断方式
                                 "sect"      = 自动（根据太阳是否在地平线以下判断）
                                 "diurnal"   = 强制白天盘
                                 "nocturnal" = 强制夜晚盘
        bounds_system          : 界体系，"Egyptian"（埃及界）或 "Ptolemaic"（托勒密界）
        minor_planet_positions : core.py 返回的小行星字典（可选）
        fixed_star_positions   : calculate_fixed_stars() 返回的恒星字典（可选）

    返回值（共 7 个字典，顺序固定）：
        planet_positions_new        主行星  （含 bound、face）
        house_positions_new         宫头    （含 bound、face）
        minor_planet_positions_new  小行星  （含 bound、face；若未传入则为空字典）
        fixed_star_positions_new    恒星    （含 bound、face；若未传入则为空字典）
        arabic_parts                阿拉伯点（含 bound、face）
        antiscia                    映点    （嵌套字典，含 planets/houses/minor_planets/fixed_stars/arabic_parts 五个子字典）
        contra_antiscia             反映点  （同上）

    访问示例：
        antiscia['planets']['Su']            # 太阳的映点
        antiscia['houses']['house 1']        # 1宫宫头的映点
        antiscia['arabic_parts']['Fortune']  # 幸运点的映点
        antiscia['minor_planets']['Ch']      # 凯龙星的映点
        antiscia['fixed_stars']['Sirius,alCMa']  # 天狼星的映点
    """

    # =========================================================================
    # 第一步：获取真实黄赤交角
    # =========================================================================
    calc_jd = jd if jd is not None else kwargs.get('jd_utc', 2451545.0)
    xx, _  = swe.calc_ut(calc_jd, swe.ECL_NUT, 0)
    eps    = xx[0]   # 真实黄赤交角（约 23.4°）

    # =========================================================================
    # 第二步：为所有输入字典追加界和面
    # =========================================================================
    planet_positions_new = add_bounds_and_faces(planet_positions, bounds_system)
    house_positions_new  = add_bounds_and_faces(house_positions,  bounds_system)

    minor_planet_positions_new = (
        add_bounds_and_faces(minor_planet_positions, bounds_system)
        if minor_planet_positions else {}
    )
    fixed_star_positions_new = (
        add_bounds_and_faces(fixed_star_positions, bounds_system)
        if fixed_star_positions else {}
    )

    # =========================================================================
    # 第三步：计算阿拉伯点（Arabic Parts / Lots）
    # =========================================================================
    arabic_parts = {}
    temp_lots    = {}   # 所有已算点（不受 selected_lots 过滤），供依赖关系使用

    if (
        'house 1' in house_positions
        and 'Su'  in planet_positions
        and 'Mo'  in planet_positions
    ):
        asc_lon   = house_positions['house 1']['lon']
        asc_speed = house_positions['house 1']['speed']
        sun_lon   = planet_positions['Su']['lon']

        # 判断日夜盘
        if lot_method == "diurnal":
            is_day = True
        elif lot_method == "nocturnal":
            is_day = False
        else:   # "sect"：太阳在地平线以下 = 夜盘
            is_day = not is_below_horizon(sun_lon, asc_lon)

        # 必须按此顺序计算，保证依赖前置（Necessity 依赖 Fortune 和 Spirit 等）
        # [修改] 已去掉所有 "Lot of " 前缀
        calculation_order = [
            "Fortune",
            "Spirit",
            "Necessity",
            "Eros",
            "Courage",
            "Victory",
            "Nemesis",
            "the Father",
            "the Mother",
            "Siblings",
            "Children",
            "Marriage",
            "Exaltation",
            "Basis",
            "Debt",
            "Chronic Illness",
            "Death",
        ]

        for lot_name in calculation_order:
            rule_info = LOT_RULES.get(lot_name, {})

            # -----------------------------------------------------------------
            # 特殊处理：基础点（Basis）
            # 取 (ASC + Fortune - Spirit) 与 (ASC + Spirit - Fortune) 中
            # 落在地平线以下（Houses 1-6）的那一个。
            # -----------------------------------------------------------------
            if rule_info.get("special") == "basis":
                if (
                    "Fortune" in temp_lots
                    and "Spirit" in temp_lots
                ):
                    fort_lon   = temp_lots["Fortune"]["lon"]
                    fort_speed = temp_lots["Fortune"]["speed"]
                    spir_lon   = temp_lots["Spirit"]["lon"]
                    spir_speed = temp_lots["Spirit"]["speed"]

                    cand1_lon   = (asc_lon + fort_lon - spir_lon) % 360.0
                    cand1_speed = asc_speed + fort_speed - spir_speed
                    cand2_lon   = (asc_lon + spir_lon - fort_lon) % 360.0
                    cand2_speed = asc_speed + spir_speed - fort_speed

                    if is_below_horizon(cand1_lon, asc_lon):
                        basis_lon, basis_speed = cand1_lon, cand1_speed
                    else:
                        basis_lon, basis_speed = cand2_lon, cand2_speed

                    temp_lots[lot_name] = {
                        "lon":   basis_lon,
                        "speed": basis_speed,
                        "lat":   0.0,
                    }
                continue   # 无论是否成功，都跳过下方通用公式

            # -----------------------------------------------------------------
            # 通用公式：lot = ASC + A - B
            # -----------------------------------------------------------------
            current_rule = rule_info.get("day") if is_day else rule_info.get("night")

            # 父亲点：土星燃烧（与太阳相距 17° 以内）时，改用木星-火星公式
            # [修改] 已去掉 "Lot of " 前缀
            if lot_name == "the Father":
                sa_lon = planet_positions.get('Sa', {}).get('lon')
                su_lon = planet_positions.get('Su', {}).get('lon')
                if sa_lon is not None and su_lon is not None:
                    diff = abs((sa_lon - su_lon + 180.0) % 360.0 - 180.0)
                    if diff < 17.0:
                        current_rule = ("Ju", "Ma")

            if not current_rule:
                continue

            a_name, b_name = current_rule

            # 处理常数度数（擢升点专用）
            if a_name == "const_19":
                a_lon, a_speed = 19.0, 0.0
            elif a_name == "const_33":
                a_lon, a_speed = 33.0, 0.0
            else:
                a_lon, a_speed = get_lon_speed(a_name, planet_positions, house_positions, temp_lots)

            if b_name == "const_19":
                b_lon, b_speed = 19.0, 0.0
            elif b_name == "const_33":
                b_lon, b_speed = 33.0, 0.0
            else:
                b_lon, b_speed = get_lon_speed(b_name, planet_positions, house_positions, temp_lots)

            if a_lon is None or b_lon is None:
                continue    # 所需天体未计算，跳过

            lot_lon   = (asc_lon + a_lon - b_lon) % 360.0
            lot_speed = asc_speed + a_speed - b_speed

            temp_lots[lot_name] = {
                "lon":   lot_lon,
                "speed": lot_speed,
                "lat":   0.0,
            }

        # 按 selected_lots 过滤，构建最终阿拉伯点字典
        for lot_name, basic_data in temp_lots.items():
            if (
                selected_lots == "all"
                or selected_lots == ["all"]
                or lot_name in selected_lots
            ):
                arabic_parts[lot_name] = build_celestial_dict(
                    basic_data["lon"],
                    0.0,
                    basic_data["speed"],
                    eps,
                    bounds_system,
                )

    # =========================================================================
    # 第四步：计算映点（Antiscia）与反映点（Contra-Antiscia）
    #
    # 映点公式：    antiscia_lon        = (180 - lon) % 360
    # 反映点公式：  contra_antiscia_lon = (360 - lon) % 360
    # 速度取反（映射方向相反）
    #
    # [修改] 按类别分别存放：planets / houses / minor_planets / fixed_stars / arabic_parts
    # =========================================================================
    antiscia = {
        'planets':       {},
        'houses':        {},
        'minor_planets': {},
        'fixed_stars':   {},
        'arabic_parts':  {},
    }
    contra_antiscia = {
        'planets':       {},
        'houses':        {},
        'minor_planets': {},
        'fixed_stars':   {},
        'arabic_parts':  {},
    }

    def _add_antiscia(name, lon, speed, category):
        """内部辅助：计算并写入单个天体的映点与反映点（按类别存放）。"""
        ant_lon    = (180.0 - lon) % 360.0
        contra_lon = (360.0 - lon) % 360.0
        antiscia[category][name]        = build_celestial_dict(ant_lon,    0.0, -speed, eps, bounds_system)
        contra_antiscia[category][name] = build_celestial_dict(contra_lon, 0.0, -speed, eps, bounds_system)

    # A. 主行星（含罗睺、计都）
    for p_name, p_data in planet_positions_new.items():
        _add_antiscia(p_name, p_data['lon'], p_data['speed'], 'planets')

    # B. 宫头
    for h_name, h_data in house_positions_new.items():
        _add_antiscia(h_name, h_data['lon'], h_data['speed'], 'houses')

    # C. 阿拉伯点
    for lot_name, lot_data in arabic_parts.items():
        _add_antiscia(lot_name, lot_data['lon'], lot_data['speed'], 'arabic_parts')

    # D. 小行星
    for mp_name, mp_data in minor_planet_positions_new.items():
        _add_antiscia(mp_name, mp_data['lon'], mp_data['speed'], 'minor_planets')

    # E. 恒星
    for star_name, star_data in fixed_star_positions_new.items():
        _add_antiscia(star_name, star_data['lon'], star_data['speed'], 'fixed_stars')

    # =========================================================================
    # 返回全部 7 个字典
    # =========================================================================
    return (
        planet_positions_new,        # 主行星（含 bound、face）
        house_positions_new,         # 宫头  （含 bound、face）
        minor_planet_positions_new,  # 小行星（含 bound、face）
        fixed_star_positions_new,    # 恒星  （含 bound、face）
        arabic_parts,                # 阿拉伯点（含 bound、face）
        antiscia,                    # 映点  （嵌套字典，按类别分组）
        contra_antiscia,             # 反映点（嵌套字典，按类别分组）
    )
