# quant_astro/core.py

import swisseph as swe
from datetime import datetime, timedelta
import re
import pandas as pd
from pathlib import Path
import warnings

# 优先使用现代 importlib.resources 替代已废弃的 pkg_resources
try:
    from importlib.resources import files
    def _get_resource_path(sub_path):
        return str(files('quant_astro').joinpath(sub_path))
except ImportError:
    import pkg_resources
    def _get_resource_path(sub_path):
        return pkg_resources.resource_filename('quant_astro', sub_path)

# --- 全局星历路径状态管理器 ---
_ACTIVE_EPHE_PATH = None

def _setup_ephe_path(ephe_path=None):
    """
    统一管理 Swiss Ephemeris 星历路径，防止多功能间互相冲掉路径配置。
    - 若显式传入 ephe_path，则更新全局路径并设置底层 C 库。
    - 若未传入且全局尚未初始化，则默认加载库内置 ephe 路径。
    - 若未传入且全局已有有效路径，则保持当前路径，不进行无故覆盖。
    """
    global _ACTIVE_EPHE_PATH
    if ephe_path is not None:
        clean_path = str(Path(ephe_path).resolve())
        swe.set_ephe_path(clean_path)
        _ACTIVE_EPHE_PATH = clean_path
    elif _ACTIVE_EPHE_PATH is None:
        try:
            bundled_ephe_path = _get_resource_path('ephe')
            swe.set_ephe_path(bundled_ephe_path)
            _ACTIVE_EPHE_PATH = bundled_ephe_path
        except Exception:
            pass
    return _ACTIVE_EPHE_PATH

def set_custom_ephe_path(ephe_path):
    """
    供外部显式全局配置高精度星历文件夹路径的公共接口。
    """
    return _setup_ephe_path(ephe_path)

# --- 辅助函数：兼容 pysweph 2.10.3.4+ 宫位元组格式 (13项或12项) ---
def _extract_12_cusps(raw_cusps):
    """
    pysweph >= 2.10.3.4 返回 13 项元组（索引 0 为空/0，索引 1..12 对应第 1..12 宫）。
    旧版本 pyswisseph 返回 12 项元组（索引 0..11 对应第 1..12 宫）。
    统一提取为长度为 12 的列表。
    """
    if len(raw_cusps) >= 13:
        return list(raw_cusps[1:13])
    return list(raw_cusps[:12])

# --- 小行星目录：代码简写 -> swisseph 内置常量 ---
# 这6个是 swisseph 标准发行版内置的，不需要额外星历文件
MINOR_PLANET_CATALOG = {
    'Ch': swe.CHIRON,   # 2060 凯龙星
    'Ph': swe.PHOLUS,   # 5145 福禄斯
    'Ce': swe.CERES,    # 1 谷神星
    'Pa': swe.PALLAS,   # 2 智神星
    'Jn': swe.JUNO,     # 3 婚神星
    'Vs': swe.VESTA,    # 4 灶神星
}

# --- 占星基础数据：庙旺陷落表 ---
PLANET_DIGNITIES = {
    'Su': {'Dom': ['Leo'], 'Exalt': ['Ari'], 'Det': ['Aqr'], 'Fall': ['Lib']},
    'Mo': {'Dom': ['Cnc'], 'Exalt': ['Tau'], 'Det': ['Cap'], 'Fall': ['Sco']},
    'Me': {'Dom': ['Gem', 'Vir'], 'Exalt': ['Vir'], 'Det': ['Sag', 'Pis'], 'Fall': ['Pis']},
    'Ve': {'Dom': ['Tau', 'Lib'], 'Exalt': ['Pis'], 'Det': ['Sco', 'Ari'], 'Fall': ['Vir']},
    'Ma': {'Dom': ['Ari', 'Sco'], 'Exalt': ['Cap'], 'Det': ['Lib', 'Tau'], 'Fall': ['Cnc']},
    'Ju': {'Dom': ['Sag', 'Pis'], 'Exalt': ['Cnc'], 'Det': ['Gem', 'Vir'], 'Fall': ['Cap']},
    'Sa': {'Dom': ['Cap', 'Aqr'], 'Exalt': ['Lib'], 'Det': ['Cnc', 'Leo'], 'Fall': ['Ari']},
    'Ur': {'Dom': ['Aqr'], 'Exalt': ['Sco'], 'Det': ['Leo'], 'Fall': ['Tau']},
    'Ne': {'Dom': ['Pis'], 'Exalt': ['Cnc'], 'Det': ['Vir'], 'Fall': ['Cap']},
    'Pl': {'Dom': ['Sco'], 'Exalt': ['Ari'], 'Det': ['Tau'], 'Fall': ['Lib']},
}

# --- 工具函数 ---
def decimal_to_dms(deg_float):
    """
    将十进制度数转换为结构化字典和字符串。
    供 chart.py 或其他模块做无计算的格式化展示使用。
    """
    d = int(deg_float)
    m_full = (deg_float - d) * 60
    m = int(m_full)
    s = round((m_full - m) * 60, 2)
    return {
        'd': d, 'm': m, 's': s,
        'str': f"{d}°{m:02d}'{s:05.2f}\""
    }

def _parse_dms(dms_str):
    # 1. 提取出度、分、秒的纯数字
    parts = re.findall(r"[\d.]+", dms_str)
    
    # 2. 先计算出坐标的十进制绝对值
    absolute_deg = float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600
    
    # 3. 捕捉负号：如果输入字符串中带有负号（代表西经或南纬），则转换为负数
    if '-' in dms_str:
        return -absolute_deg
    return absolute_deg

def _parse_timezone(tz_str):
    match = re.match(r'^([+-]?)(\d{1,2})(:?)(\d{0,2})$', tz_str)
    sign = -1 if match.group(1) == '-' else 1
    hours = float(match.group(2))
    mins = float(match.group(4) or 0)
    return sign * (hours + mins/60)

# --- 历法转换辅助函数 ---
def _parse_local_time_and_convert_to_gregorian(local_time_str, calendar='g'):
    """
    解析本地时间字符串，统一转换为格里历 datetime 对象，无精度损失。
    """
    try:
        dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S")

    if calendar.lower() == 'g':
        return dt  # 已是格里历，直接返回

    # 儒略历 -> 格里历：通过 swe 官方函数精确转换
    hour_dec = (dt.hour
                + dt.minute / 60.0
                + dt.second / 3600.0
                + dt.microsecond / 3600000000.0)

    # 按儒略历日期计算儒略日（JD）
    jd = swe.julday(dt.year, dt.month, dt.day, hour_dec, swe.JUL_CAL)

    # 将 JD 转回格里历
    g_year, g_month, g_day, g_h_dec = swe.revjul(jd, swe.GREG_CAL)

    # 将格里历小时小数拆回时、分、秒、微秒
    g_h  = int(g_h_dec)
    g_md = (g_h_dec - g_h) * 60.0
    g_m  = int(g_md)
    g_sd = (g_md - g_m) * 60.0
    g_s  = int(g_sd)
    g_us = round((g_sd - g_s) * 1_000_000)

    return datetime(int(g_year), int(g_month), int(g_day), g_h, g_m, g_s, g_us)

# --- 主计算函数 ---
def calculate_positions(
    local_time_str, timezone_str, latitude_str, longitude_str, elevation=0.0,
    ecliptic_mode='sidereal', ayanamsha_mode='SIDM_KRISHNAMURTI',
    node_mode='mean', house_system='Placidus', ephe_path=None, 
    strict_ephe=True, **kwargs
):
    """
    计算给定时间和地点的行星和宫位位置。
    
    参数:
        strict_ephe (bool): 
            若为 True（默认），当请求 Swiss Ephemeris 高精度计算却因缺少 .se1 文件导致
            底层静默回退为 Moshier 粗算公式时，立即抛出 FileNotFoundError；
            若为 False，则仅发出警告并继续使用粗算值。
    """
    # 统一设置星历路径，不覆盖已有有效配置
    current_ephe_dir = _setup_ephe_path(ephe_path)

    # 智能转换岁差模式：支持字符串输入
    real_ayanamsha_mode = ayanamsha_mode
    
    if isinstance(ayanamsha_mode, str):
        clean_name = ayanamsha_mode.replace("swe.", "").strip()
        if hasattr(swe, clean_name):
            real_ayanamsha_mode = getattr(swe, clean_name)
        elif hasattr(swe, f"SE_{clean_name}"):
            real_ayanamsha_mode = getattr(swe, f"SE_{clean_name}")
        elif hasattr(swe, clean_name.replace("SIDM_", "SE_SIDM_")):
            real_ayanamsha_mode = getattr(swe, clean_name.replace("SIDM_", "SE_SIDM_"))
        else:
            raise ValueError(f"❌ 找不到岁差模式名称: {ayanamsha_mode}。请检查拼写是否与 swisseph 常量一致。")

    # 1. 解析输入参数
    calendar = kwargs.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_time_str, calendar)
    latitude = _parse_dms(latitude_str)
    longitude = _parse_dms(longitude_str)
    timezone_offset = _parse_timezone(timezone_str)

    # 2. 计算儒略日 (Julian Day)
    utc_time = local_dt - timedelta(hours=timezone_offset)
    jd_utc = swe.julday(
        utc_time.year, utc_time.month, utc_time.day,
        utc_time.hour + utc_time.minute / 60.0
            + utc_time.second / 3600.0
            + utc_time.microsecond / 3600000000.0,
        swe.GREG_CAL
    )

    # 预先计算真实黄赤交角，使用 [0] 避免 2/3 参数解包不匹配
    _eps_raw = swe.calc_ut(jd_utc, swe.ECL_NUT, 0)[0]
    eps = _eps_raw[0]  # 真实黄赤交角（度），约 23.4°

    # 3. 设置星历计算标志
    if ecliptic_mode == 'sidereal':
        swe.set_sid_mode(real_ayanamsha_mode)
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED
        house_flag = swe.FLG_SIDEREAL
    else:
        flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        house_flag = 0

    # 4. 计算行星位置
    planet_positions = {}     
    dignity_results = PLANET_DIGNITIES.copy()

    node_flag = swe.TRUE_NODE if node_mode == 'true' else swe.MEAN_NODE
    planet_map = {
        swe.SUN: 'Su', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve',
        swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur',
        swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl', node_flag: 'Ra'
    }

    selected_minor_planets = kwargs.get('selected_minor_planets', [])
    for code in selected_minor_planets:
        if code in MINOR_PLANET_CATALOG:
            planet_map[MINOR_PLANET_CATALOG[code]] = code

    selected_planets = kwargs.get('selected_planets', None)

    for p_id, name in planet_map.items():
        should_calc = False
        if selected_planets is None or 'All' in selected_planets:
            should_calc = True
        else:
            if name in selected_planets:
                should_calc = True
            if p_id == node_flag and ('Ra' in selected_planets or 'Ke' in selected_planets):
                should_calc = True
            if name in selected_minor_planets:
                should_calc = True
        
        if not should_calc:
            continue

        # 执行黄道坐标计算并捕获返回标志
        calc_res = swe.calc_ut(jd_utc, p_id, flag)
        xx = calc_res[0]
        ret_flag = calc_res[1] if len(calc_res) > 1 and isinstance(calc_res[1], int) else None

        # 校验是否发生静默降级（毛病一修复）
        if (flag & swe.FLG_SWIEPH) and ret_flag is not None:
            is_moseph = bool(hasattr(swe, 'FLG_MOSEPH') and (ret_flag & swe.FLG_MOSEPH))
            is_missing_swieph = not bool(ret_flag & swe.FLG_SWIEPH)
            if is_moseph or is_missing_swieph:
                err_msg = (
                    f"❌ 高精度星历缺失：计算 '{name}' (ID: {p_id}) 在 JD {jd_utc:.4f} 处未能加载 "
                    f"Swiss Ephemeris 高精度数据文件 (.se1)，底层已静默降级为 Moshier 粗算公式。"
                    f"当前星历搜索路径为: '{current_ephe_dir}'。"
                )
                if strict_ephe:
                    raise FileNotFoundError(err_msg)
                else:
                    warnings.warn(err_msg, RuntimeWarning)

        # 执行赤道坐标计算
        calc_eq_res = swe.calc_ut(jd_utc, p_id, flag | swe.FLG_EQUATORIAL)
        xx_eq = calc_eq_res[0]
        
        if name != 'Ra' or (selected_planets is None or 'All' in selected_planets or 'Ra' in selected_planets):
            planet_positions[name] = {
                'lon': xx[0] % 360,
                'lat': xx[1],
                'speed': xx[3],
                'ra': xx_eq[0],
                'dec': xx_eq[1],
                'dec_speed': xx_eq[4]
            }
        
        if p_id == node_flag:
            if selected_planets is None or 'All' in selected_planets or 'Ke' in selected_planets:
                south_lon = (xx[0] + 180) % 360
                south_lat = -xx[1]
                pos_ecl_south = (south_lon, south_lat, xx[2])
                pos_eq_south = swe.cotrans(pos_ecl_south, eps)
                planet_positions['Ke'] = {
                    'lon': south_lon,
                    'lat': south_lat,
                    'speed': xx[3],
                    'ra': pos_eq_south[0],
                    'dec': pos_eq_south[1],
                    'dec_speed': -xx_eq[4]
                }

    # 5. 计算宫位位置
    house_positions = {}
    house_codes = {
        'Placidus': b'P',
        'Koch': b'K',
        'Regiomontanus': b'R',
        'Whole Sign': b'W',
        'Equal': b'E',
        'Campanus': b'C',
        'Alcabitius': b'B',
        'Porphyry': b'O',
        'Morinus': b'M',
        'Topocentric': b'T',
        'Vehlow': b'V',
        'Meridian': b'X',
        'Horizon': b'H',
        'Gauquelin': b'G',
        'Krusinski': b'U',
        'Carter': b'F',
        'Equal/MC': b'D',
        'Equal/Zodiac': b'N',
        'APC': b'Y'
    }
    
    if house_system in house_codes:
        target_asc = None
        jd_for_houses = jd_utc

        kp_horary_params = kwargs.get("KP_HORARY", None)

        if kp_horary_params and kp_horary_params.get('is_active', False):
            print("🔮 已进入卜卦计算模式（仅调整宫位）...")
            horary_mode = kp_horary_params.get("mode")
            horary_number = kp_horary_params.get("number")

            if not horary_mode or horary_number is None:
                raise ValueError("卜卦字典中缺少 'mode' 或 'number' 参数。")

            csv_path = _get_resource_path('data/sub-sub.csv')
            df = pd.read_csv(csv_path)
            
            if horary_mode.upper() == "KS-N":
                COLUMN, RESULT_COLUMN = "KS-N", "KS-D"
            else:
                COLUMN, RESULT_COLUMN = "CIL-N", "From"
                
            target_row = df[df[COLUMN] == horary_number]
            if target_row.empty:
                raise ValueError(f"在卜卦文件中找不到编号 {horary_number}")
            target_asc = float(target_row.iloc[0][RESULT_COLUMN])
            
            def find_correct_time(target_asc_lon, initial_jd, lat, lon, hs_code, flags, tolerance=1e-7, max_iter=100):
                jd_low, jd_high = initial_jd - 1.0, initial_jd + 1.0
                for _ in range(max_iter):
                    jd_mid = (jd_low + jd_high) / 2
                    houses_mid_raw = swe.houses_ex(jd_mid, lat, lon, hs_code, flags=flags)[0]
                    houses_mid = _extract_12_cusps(houses_mid_raw)
                    current_asc = houses_mid[0] % 360
                    diff = (current_asc - target_asc_lon + 180) % 360 - 180
                    if abs(diff) < tolerance:
                        return jd_mid
                    if diff > 0:
                        jd_high = jd_mid
                    else:
                        jd_low = jd_mid
                return jd_mid

            house_flag = swe.FLG_SIDEREAL if ecliptic_mode == 'sidereal' else 0
            hs_code_bytes = house_codes.get(house_system)
            
            jd_for_houses = find_correct_time(target_asc, jd_utc, latitude, longitude, hs_code_bytes, house_flag)

        res_h = swe.houses_ex2(
            jd_for_houses, latitude, longitude, house_codes[house_system], flags=house_flag
        )
        houses_raw = res_h[0]
        ascmc = res_h[1]
        houses_speed_raw = res_h[2]
        
        houses = _extract_12_cusps(houses_raw)
        houses_speed = _extract_12_cusps(houses_speed_raw)
        
        for i, cusp_lon in enumerate(houses):
            final_lon = cusp_lon % 360
            
            if target_asc is not None:
                if i == 0:
                    final_lon = target_asc
                elif i == 6:
                    final_lon = (target_asc + 180.0) % 360.0

            current_speed = houses_speed[i]

            pos_ecl = (final_lon, 0.0, 1.0)
            pos_eq = swe.cotrans(pos_ecl, eps)
            house_positions[f"house {i+1}"] = {
                'lon': final_lon,
                'lat': 0.0,
                'speed': current_speed,
                'ra': pos_eq[0],
                'dec': pos_eq[1],
                'dec_speed': 0.0
            }

    # 按照用户配置顺序重组字典
    if selected_planets and 'All' not in selected_planets:
        ordered_pos = {k: planet_positions[k] for k in selected_planets if k in planet_positions}
        for k, v in planet_positions.items():
            if k not in ordered_pos:
                ordered_pos[k] = v
        planet_positions = ordered_pos

    # 把字典分拣成"主行星"和"小行星"两个
    MAIN_PLANETS = {'Su', 'Mo', 'Me', 'Ve', 'Ma', 'Ju', 'Sa', 'Ur', 'Ne', 'Pl', 'Ra', 'Ke'}

    main_planet_positions = {}
    minor_planet_positions = {}

    for key, value in planet_positions.items():
        if key in MAIN_PLANETS:
            main_planet_positions[key] = value
        else:
            minor_planet_positions[key] = value
    
    return main_planet_positions, house_positions, ascmc, jd_utc, dignity_results, minor_planet_positions

# --- 独立计算函数：日出与值日星 ---
def get_sun_rise_and_lord(birth_config, sunrise_config, ephe_path=None):
    """
    独立计算日出时间及值日星。
    支持传入 ephe_path 或从 birth_config 中读取 ephe_path，不会覆写已有的全局星历配置。
    """
    effective_ephe_path = ephe_path or birth_config.get('ephe_path')
    _setup_ephe_path(effective_ephe_path)

    lat = _parse_dms(birth_config['latitude_str'])
    lon = _parse_dms(birth_config['longitude_str'])
    alt = birth_config.get('elevation', 0.0)
    
    local_dt_str = birth_config['local_time_str']
    calendar = birth_config.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_dt_str, calendar)

    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    tz_offset = _parse_timezone(birth_config['timezone_str'])
    utc_midnight = local_midnight - timedelta(hours=tz_offset)
    
    jd_start = swe.julday(
        utc_midnight.year, utc_midnight.month, utc_midnight.day,
        utc_midnight.hour + utc_midnight.minute/60.0 + utc_midnight.second/3600.0
    )

    press = birth_config.get('atpress', 1013.25) 
    temp = birth_config.get('attemp', 10.0)  
    rsmi = sunrise_config.get('rsmi', swe.CALC_RISE | swe.BIT_DISC_CENTER)
    
    try:
        geopos = (lon, lat, alt)
        res = swe.rise_trans(
            jd_start,
            swe.SUN,
            rsmi,
            geopos,
            press,
            temp,
            swe.FLG_SWIEPH
        )
        
        rise_jd = 0.0
        ret_flag = -1
        
        if isinstance(res, tuple):
            if isinstance(res[0], int) and len(res) > 1 and isinstance(res[1], (tuple, list)):
                ret_flag = res[0]
                rise_jd = res[1][0]
            elif isinstance(res[0], (tuple, list)) and len(res) > 1 and isinstance(res[1], int):
                ret_flag = res[1]
                rise_jd = res[0][0]
            elif isinstance(res[0], float):
                ret_flag = 0
                rise_jd = res[0]
        
        if ret_flag < 0 or rise_jd <= 1.0:
            return {'error': f"Sunrise not found. Flag={ret_flag}, JD={rise_jd}. (Polar region?)"}
            
    except (swe.Error, Exception) as e:
        return {'error': f"SwissEph Error: {e}"}

    try:
        y, m, d, h_decimal = swe.revjul(rise_jd)
        
        h = int(h_decimal)
        min_full = (h_decimal - h) * 60
        mi = int(min_full)
        s = (min_full - mi) * 60
        micro = int((s - int(s)) * 1000000)
        
        rise_dt_utc = datetime(y, m, d, h, mi, int(s), micro)
        rise_dt_local = rise_dt_utc + timedelta(hours=tz_offset)
        
    except ValueError as e:
        return {'error': f"Date Conversion Error: {e} (JD={rise_jd})"}

    current_iso_weekday = local_dt.weekday()
    
    if local_dt < rise_dt_local:
        effective_weekday = (current_iso_weekday - 1) % 7
    else:
        effective_weekday = current_iso_weekday

    chaldean_map = {
        0: 'Mo', 1: 'Ma', 2: 'Me', 3: 'Ju', 4: 'Ve', 5: 'Sa', 6: 'Su'
    }
    
    return {
        'sunrise_time_local': str(rise_dt_local),
        'day_lord': chaldean_map.get(effective_weekday, 'Unknown'),
        'is_before_sunrise': local_dt < rise_dt_local
    }

# --- 独立函数：计算恒星位置 ---
def calculate_fixed_stars(
    jd_utc, selected_stars, ecliptic_mode='tropical', 
    ayanamsha_mode='SIDM_KRISHNAMURTI', ephe_path=None, strict_ephe=True
):
    """
    计算给定儒略日下，一组恒星的位置。
    支持显式 ephe_path 注入，并校验恒星数据文件缺失时的降级行为。
    """
    current_ephe_dir = _setup_ephe_path(ephe_path)

    if ecliptic_mode == 'sidereal':
        if isinstance(ayanamsha_mode, str):
            clean_name = ayanamsha_mode.replace("swe.", "").strip()
            if hasattr(swe, clean_name):
                swe.set_sid_mode(getattr(swe, clean_name))
            elif hasattr(swe, f"SE_{clean_name}"):
                swe.set_sid_mode(getattr(swe, f"SE_{clean_name}"))
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED
    else:
        flag = swe.FLG_SWIEPH | swe.FLG_SPEED

    fixed_star_positions = {}

    for star_name in selected_stars:
        try:
            res_star = swe.fixstar2_ut(star_name, jd_utc, flag)
            xx = res_star[0]
            ret_flag = res_star[2] if len(res_star) >= 3 and isinstance(res_star[2], int) else (
                res_star[1] if len(res_star) == 2 and isinstance(res_star[1], int) else None
            )

            # 校验恒星高精度文件
            if (flag & swe.FLG_SWIEPH) and ret_flag is not None:
                is_moseph = bool(hasattr(swe, 'FLG_MOSEPH') and (ret_flag & swe.FLG_MOSEPH))
                is_missing_swieph = not bool(ret_flag & swe.FLG_SWIEPH)
                if is_moseph or is_missing_swieph:
                    err_msg = (
                        f"❌ 恒星数据缺失：计算恒星 '{star_name}' 时未能加载对应高精度数据文件。"
                        f"当前星历搜索路径为: '{current_ephe_dir}'。"
                    )
                    if strict_ephe:
                        raise FileNotFoundError(err_msg)
                    else:
                        warnings.warn(err_msg, RuntimeWarning)

            res_star_eq = swe.fixstar2_ut(star_name, jd_utc, flag | swe.FLG_EQUATORIAL)
            xx_eq = res_star_eq[0]

            fixed_star_positions[star_name] = {
                'lon':       xx[0] % 360,
                'lat':       xx[1],
                'speed':     xx[3],
                'ra':        xx_eq[0],
                'dec':       xx_eq[1],
                'dec_speed': xx_eq[4]
            }

        except Exception as e:
            if strict_ephe and isinstance(e, FileNotFoundError):
                raise e
            print(f"⚠️ 恒星 '{star_name}' 计算失败，已跳过。原因：{e}")
            continue

    return fixed_star_positions

# --- 计算行星时 (Planetary Hour) ---
def get_planetary_hour(birth_config, sunrise_config, ephe_path=None):
    """
    计算当前时间对应的行星时 (Planetary Hour)。
    逻辑：根据日出日落将白天和黑夜各分12等分，起始星为值日星，按迦勒底序列顺推。
    支持传入 ephe_path 或从 birth_config 中读取 ephe_path，保持全局星历路径稳定。
    """
    effective_ephe_path = ephe_path or birth_config.get('ephe_path')
    _setup_ephe_path(effective_ephe_path)

    lat = _parse_dms(birth_config['latitude_str'])
    lon = _parse_dms(birth_config['longitude_str'])
    alt = birth_config.get('elevation', 0.0)
    tz_offset = _parse_timezone(birth_config['timezone_str'])
    
    local_dt_str = birth_config['local_time_str']
    calendar = birth_config.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_dt_str, calendar)

    def calc_sun_events(target_date):
        midnight_local = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_utc = midnight_local - timedelta(hours=tz_offset)
        jd_start = swe.julday(
            midnight_utc.year, midnight_utc.month, midnight_utc.day,
            midnight_utc.hour + midnight_utc.minute/60.0
        )
        
        geopos = (lon, lat, alt)
        press = birth_config.get('atpress', 1013.25)
        temp = birth_config.get('attemp', 10.0)
        
        user_rsmi = sunrise_config.get('rsmi', swe.CALC_RISE | swe.BIT_DISC_CENTER)
        style_flags = user_rsmi & ~swe.CALC_RISE & ~swe.CALC_SET
        
        flag_rise = swe.CALC_RISE | style_flags
        flag_set = swe.CALC_SET | style_flags

        res_rise = swe.rise_trans(jd_start, swe.SUN, flag_rise, geopos, press, temp, swe.FLG_SWIEPH)
        rise_jd = res_rise[1][0] if isinstance(res_rise[1], (tuple, list)) else res_rise[0][0] 
        
        res_set = swe.rise_trans(jd_start, swe.SUN, flag_set, geopos, press, temp, swe.FLG_SWIEPH)
        set_jd = res_set[1][0] if isinstance(res_set[1], (tuple, list)) else res_set[0][0]

        def jd_to_local(jd_val):
            y, m, d, h_dec = swe.revjul(jd_val)
            h = int(h_dec)
            mn = int((h_dec - h) * 60)
            s = (h_dec - h - mn/60) * 3600
            dt_utc = datetime(y, m, d, h, mn, int(s), int((s-int(s))*1000000))
            return dt_utc + timedelta(hours=tz_offset)

        return jd_to_local(rise_jd), jd_to_local(set_jd)

    rise_today, set_today = calc_sun_events(local_dt)
    
    is_day_time = False
    start_time = None
    end_time = None
    astrological_day_start = None
    
    if local_dt < rise_today:
        rise_prev, set_prev = calc_sun_events(local_dt - timedelta(days=1))
        is_day_time = False
        start_time = set_prev
        end_time = rise_today
        astrological_day_start = rise_prev
        
    elif local_dt >= set_today:
        rise_next, set_next = calc_sun_events(local_dt + timedelta(days=1))
        is_day_time = False
        start_time = set_today
        end_time = rise_next
        astrological_day_start = rise_today
        
    else:
        is_day_time = True
        start_time = rise_today
        end_time = set_today
        astrological_day_start = rise_today

    total_duration = (end_time - start_time).total_seconds()
    elapsed = (local_dt - start_time).total_seconds()
    hour_length = total_duration / 12.0
    
    hour_idx = int(elapsed / hour_length)
    if hour_idx >= 12:
        hour_idx = 11

    chaldean_order = ['Sa', 'Ju', 'Ma', 'Su', 'Ve', 'Me', 'Mo']
    weekday_map = {0: 6, 1: 2, 2: 5, 3: 1, 4: 4, 5: 0, 6: 3}
    
    astro_weekday = astrological_day_start.weekday()
    day_lord_idx = weekday_map[astro_weekday]
    
    offset = hour_idx
    if not is_day_time:
        offset += 12
        
    final_idx = (day_lord_idx + offset) % 7
    planet_lord = chaldean_order[final_idx]

    return {
        'planetary_hour_lord': planet_lord,
        'is_day_time': is_day_time,
        'hour_index': hour_idx + 1,
        'hour_start': str(start_time + timedelta(seconds=hour_idx*hour_length)),
        'hour_end': str(start_time + timedelta(seconds=(hour_idx+1)*hour_length))
    }