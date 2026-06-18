# quant_astro/core.py

import swisseph as swe
from datetime import datetime, timedelta
import pytz
import re
import pkg_resources
import pandas as pd

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

# --- 新增工具函数 ---
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
# --------------------

# (从你原始代码中提取的辅助函数)
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
    local_time_str, timezone_str, latitude_str, longitude_str, elevation,
    ecliptic_mode='sidereal', ayanamsha_mode='SIDM_KRISHNAMURTI',
    node_mode='mean', house_system='Placidus', ephe_path=None, 
    **kwargs
):
    """
    计算给定时间和地点的行星和宫位位置。
    如果提供了 ephe_path，则使用它。否则，使用库内置的星历文件。
    """


    # =========================================================================
    # [新增] 智能转换岁差模式：支持字符串输入
    # 允许输入 "swe.SIDM_KRISHNAMURTI" 或 "SIDM_KRISHNAMURTI"
    # =========================================================================
    real_ayanamsha_mode = ayanamsha_mode # 默认先拿过来
    
    if isinstance(ayanamsha_mode, str):
        # 1. 去掉可能误写的 "swe." 前缀，只保留大写变量名
        clean_name = ayanamsha_mode.replace("swe.", "").strip()
        
        # 2. 从 swisseph 库中动态查找这个名字对应的数字
        if hasattr(swe, clean_name):
            real_ayanamsha_mode = getattr(swe, clean_name)
        else:
            # 如果名字写错了，给个报错或者默认值
            raise ValueError(f"❌ 找不到岁差模式名称: {ayanamsha_mode}。请检查拼写是否与 swisseph 常量一致。")
    # =========================================================================


    # 修改点2：根据 ephe_path 是否提供来设置星历路径
    if ephe_path:
        # 用户提供了外部路径，使用它
        swe.set_ephe_path(ephe_path)
    else:
        # 用户未提供路径，使用包内自带的路径
        # 这会自动找到 site-packages/quant_astro/ephe/ 这个目录
        bundled_ephe_path = pkg_resources.resource_filename('quant_astro', 'ephe')
        swe.set_ephe_path(bundled_ephe_path)

    # 1. 解析输入参数
    # 立即按指定历法（'g'=格里历，'j'=儒略历）将时间无损统一转换为格里历
    calendar = kwargs.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_time_str, calendar)
    latitude = _parse_dms(latitude_str)
    longitude = _parse_dms(longitude_str)
    timezone_offset = _parse_timezone(timezone_str)

    # 2. 计算儒略日 (Julian Day)
    # local_dt 已确保为格里历，显式传入 swe.GREG_CAL，并保留微秒精度
    utc_time = local_dt - timedelta(hours=timezone_offset)
    jd_utc = swe.julday(
        utc_time.year, utc_time.month, utc_time.day,
        utc_time.hour + utc_time.minute / 60.0
            + utc_time.second / 3600.0
            + utc_time.microsecond / 3600000000.0,
        swe.GREG_CAL
    )

    # [新增] 预先计算真实黄赤交角，供后续所有 swe.cotrans() 使用
    # swe.ECL_NUT (= -1)：swisseph 内置伪天体，专用于返回章动与黄赤交角
    _eps_raw, _ = swe.calc_ut(jd_utc, swe.ECL_NUT, 0)
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

    # ----------------- [修改] 强制输出所有行星的庙旺配置，不过滤 -----------------
    dignity_results = PLANET_DIGNITIES.copy() 
    # ----------------- [修改结束] -----------------

    node_flag = swe.TRUE_NODE if node_mode == 'true' else swe.MEAN_NODE
    # 主行星（固定，不受配置影响）
    planet_map = {
        swe.SUN: 'Su', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve',
        swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur',
        swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl', node_flag: 'Ra'
    }

    # 小行星（根据配置动态添加）
    selected_minor_planets = kwargs.get('selected_minor_planets', [])
    for code in selected_minor_planets:
        if code in MINOR_PLANET_CATALOG:
            planet_map[MINOR_PLANET_CATALOG[code]] = code

    # 获取用户选择的行星列表，如果未提供则默认为 None (即全选)
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
                # 小行星豁免：在 selected_minor_planets 配置里的星体，跳过主行星过滤
            if name in selected_minor_planets:
                should_calc = True
        
        if not should_calc:
            continue
        # === 【新增】填充庙旺陷落字典 ===
        # 逻辑：只要不是南北交点(Ra/Ke)，且在我们的配置表中存在，就加入结果
        # ------------------------------------

        xx, _ = swe.calc_ut(jd_utc, p_id, flag)
        xx_eq, _ = swe.calc_ut(jd_utc, p_id, flag | swe.FLG_EQUATORIAL)
        
        # 存储逻辑：检查是否需要保存该具体行星
        # 对于普通行星和 Ra：
        if name != 'Ra' or (selected_planets is None or 'All' in selected_planets or 'Ra' in selected_planets):
            planet_positions[name] = {'lon': xx[0] % 360, 'lat': xx[1], 'speed': xx[3], 'ra': xx_eq[0], 'dec': xx_eq[1], 'dec_speed': xx_eq[4]}
        
        # 对于计都 (Ke) 的特殊处理：
        if p_id == node_flag:
            # 只有当全选，或者明确选择了 'Ke' 时，才计算并存储 Ke
            if selected_planets is None or 'All' in selected_planets or 'Ke' in selected_planets:
                south_lon = (xx[0] + 180) % 360
                south_lat = -xx[1]
                pos_ecl_south = (south_lon, south_lat, xx[2])
                pos_eq_south = swe.cotrans(pos_ecl_south, eps)
                planet_positions['Ke'] = {'lon': south_lon, 'lat': south_lat, 'speed': xx[3], 'ra': pos_eq_south[0], 'dec': pos_eq_south[1], 'dec_speed': -xx_eq[4]}


    # 5. 计算宫位位置
    house_positions = {}
    house_codes = {'Placidus': b'P', 'Koch': b'K', 'Regiomontanus': b'R', 'Whole Sign': b'W', 'Equal': b'E', 'Campanus': 'C'}
    
    if house_system in house_codes:
        target_asc = None  # <---【新增】初始化变量，防止非卜卦模式下报错
            # --- 在计算宫位前，增加这些代码 ---
        jd_for_houses = jd_utc  # 默认情况下，用原始时间计算宫位

        # 接着，从kwargs中获取KP卜卦的设置字典
        kp_horary_params = kwargs.get("KP_HORARY", None)

        # 如果启动了卜卦模式，则重新计算用于宫位的时间
        if kp_horary_params and kp_horary_params.get('is_active', False):
            print("🔮 已进入卜卦计算模式（仅调整宫位）...")
            horary_mode = kp_horary_params.get("mode")
            horary_number = kp_horary_params.get("number")

            if not horary_mode or horary_number is None:
                raise ValueError("卜卦字典中缺少 'mode' 或 'number' 参数。")

            csv_path = pkg_resources.resource_filename('quant_astro', 'data/sub-sub.csv')
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
                    houses_mid = swe.houses_ex(jd_mid, lat, lon, hs_code, flags=flags)[0]
                    current_asc = houses_mid[0] % 360
                    diff = (current_asc - target_asc_lon + 180) % 360 - 180
                    if abs(diff) < tolerance:
                        return jd_mid
                    if diff > 0:
                        jd_high = jd_mid
                    else:
                        jd_low = jd_mid
                return jd_mid

            house_codes_map = {'Placidus': b'P', 'Koch': b'K', 'Regiomontanus': b'R', 'Whole Sign': b'W', 'Equal': b'E', 'Campanus': 'C'}
            house_flag = swe.FLG_SIDEREAL if ecliptic_mode == 'sidereal' else 0
            hs_code_bytes = house_codes_map.get(house_system)
            
            # 关键：用搜索到的新时间，覆盖用于计算宫位的时间
            jd_for_houses = find_correct_time(target_asc, jd_utc, latitude, longitude, hs_code_bytes, house_flag)
        

        
        # 原始计算宫位代码

        houses, ascmc, houses_speed, ascmc_speed = swe.houses_ex2(
                jd_for_houses, latitude, longitude, house_codes[house_system], flags=house_flag
            )
        
        for i, cusp_lon in enumerate(houses[:12]):
            # === 【修改开始：同时修正1宫和7宫】 ===
            # 1. 先默认使用反推计算出来的度数
            final_lon = cusp_lon % 360
            
            # 2. 如果 target_asc 有值 (说明在卜卦模式下)，则进行强制修正
            if target_asc is not None:
                if i == 0:
                    # 第1宫：直接使用查表数据
                    final_lon = target_asc
                elif i == 6:
                    # 第7宫：是第1宫的对面，直接 +180 度
                    final_lon = (target_asc + 180.0) % 360.0
            # === 【修改结束】 ===

            # ----------------- [新增] 将 speed 写入字典 -----------------
            # 注意：houses_speed[i] 就是对应宫头的日速度 (度/天)
            current_speed = houses_speed[i]

            pos_ecl = (final_lon, 0.0, 1.0)
            pos_eq = swe.cotrans(pos_ecl, eps)
            # 注意：这里的 'lon' 用的是 final_lon
            house_positions[f"house {i+1}"] = {'lon': final_lon, 'lat': 0.0, 'speed': current_speed, 'ra': pos_eq[0], 'dec': pos_eq[1], 'dec_speed': 0.0}


    # ----------------- [新增] 按照用户配置顺序重组字典 -----------------
    if selected_planets and 'All' not in selected_planets:
        # 1. 重排行星位置字典
        # 逻辑：遍历用户输入的 list，如果该行星在计算结果里存在，就按顺序提出来
        ordered_pos = {k: planet_positions[k] for k in selected_planets if k in planet_positions}
        
        # 处理可能的漏网之鱼（比如代码自动生成的 Ke，如果没在 selected_planets 里显式写 Ke 但写了 Ra）
        # 如果您希望完全严格遵守输入，上面的 ordered_pos 足够了。
        # 这里为了保险，把不在列表里的追加到后面（通常不会发生，除非逻辑特殊）
        for k, v in planet_positions.items():
            if k not in ordered_pos:
                ordered_pos[k] = v
        planet_positions = ordered_pos
    # ----------------- [新增结束] -----------------

    # ----------------- [新增] 把字典分拣成"主行星"和"小行星"两个 -----------------
    # 定义哪些 key 属于主行星（七大行星 + 三王星 + 罗睺计都）
    MAIN_PLANETS = {'Su', 'Mo', 'Me', 'Ve', 'Ma', 'Ju', 'Sa', 'Ur', 'Ne', 'Pl', 'Ra', 'Ke'}

    # 遍历完整字典，按 key 分拣到两个新字典里
    main_planet_positions = {}
    minor_planet_positions = {}

    for key, value in planet_positions.items():
        if key in MAIN_PLANETS:
            main_planet_positions[key] = value
        else:
            minor_planet_positions[key] = value
    # ----------------- [分拣结束] -----------------
    
    return main_planet_positions, house_positions, ascmc, jd_utc, dignity_results, minor_planet_positions


    # ----------------- [新增] 独立计算函数：日出与值日星 -----------------
def get_sun_rise_and_lord(birth_config, sunrise_config):
    """
    独立计算日出时间及值日星。
    [修复版 V5] 针对 pyswisseph 2.10+ 的最终修正：
    1. 函数签名调整为 (jd, body, rsmi, geopos, press, temp, flags)。
    2. 修复返回值解析逻辑：(int_flag, (jd, ...))。
    3. 移除不存在的 get_ephe_path 调用。
    """
    

    # --- 确保星历路径已设置 ---
    # pyswisseph 没有 get_ephe_path，因此我们直接尝试设置路径。
    # 这能防止因路径丢失导致的 calculation error (return 0.0)。
    try:
        bundled_ephe_path = pkg_resources.resource_filename('quant_astro', 'ephe')
        swe.set_ephe_path(bundled_ephe_path)
    except Exception:
        pass 

    # 2. 获取参数
    lat = _parse_dms(birth_config['latitude_str'])
    lon = _parse_dms(birth_config['longitude_str'])
    alt = birth_config.get('elevation', 0.0)
    
    # 3. 确定搜索起始时间
    local_dt_str = birth_config['local_time_str']
    calendar = birth_config.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_dt_str, calendar)

    # 设为当天 00:00:00，搜索当天的日出
    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    tz_offset = _parse_timezone(birth_config['timezone_str'])
    utc_midnight = local_midnight - timedelta(hours=tz_offset)
    
    jd_start = swe.julday(utc_midnight.year, utc_midnight.month, utc_midnight.day,
                          utc_midnight.hour + utc_midnight.minute/60.0 + utc_midnight.second/3600.0)

    # 气象与标志位
    press = birth_config.get('atpress', 1013.25) 
    temp = birth_config.get('attemp', 10.0)  
    rsmi = sunrise_config.get('rsmi', swe.CALC_RISE | swe.BIT_DISC_CENTER)
    
    # 4. 调用 swisseph 计算日出
    try:
        geopos = (lon, lat, alt)
        
        # [核心修正] 2.10+ 版本签名: (tjd, body, rsmi, geopos, atpress, attemp, flags)
        res = swe.rise_trans(
            jd_start,         # Arg 1: Julian Day
            swe.SUN,          # Arg 2: Body (int for planet)
            rsmi,             # Arg 3: RSMI (Rise flag)
            geopos,           # Arg 4: Geopos Tuple
            press,            # Arg 5: Pressure
            temp,             # Arg 6: Temperature
            swe.FLG_SWIEPH    # Arg 7: Ephemeris Flags
        )
        
        # [返回值解析修正]
        # pyswisseph 2.10+ rise_trans 返回格式通常为: (ret_flag, (jd_rise, ...))
        # res[0] 是状态码 (0=OK, -1=Error, -2=Circumpolar)
        # res[1] 是结果元组 (jd, ...)
        
        rise_jd = 0.0
        ret_flag = -1
        
        # 智能判断返回值结构
        if isinstance(res, tuple):
            # 情况 A: (flag, (values...)) -> 新版常见
            if isinstance(res[0], int) and len(res) > 1 and isinstance(res[1], tuple):
                ret_flag = res[0]
                rise_jd = res[1][0]
            # 情况 B: ((values...), flag) -> 旧版或 calc_ut 常见
            elif isinstance(res[0], tuple) and len(res) > 1 and isinstance(res[1], int):
                ret_flag = res[1]
                rise_jd = res[0][0]
            # 情况 C: 仅返回 (values...) -> 罕见
            elif isinstance(res[0], float):
                ret_flag = 0
                rise_jd = res[0]
        
        # 有效性检查
        if ret_flag < 0 or rise_jd <= 1.0: # JD 必须大于 1.0 (公元前4713年之前为0或负)
            return {'error': f"Sunrise not found. Flag={ret_flag}, JD={rise_jd}. (Polar region?)"}
            
    except swe.Error as e:
        return {'error': f"SwissEph Error: {e}"}

    # 5. 将日出时间转回本地时间
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

    # 6. 计算值日星
    current_iso_weekday = local_dt.weekday() # 0=Mon
    
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

# ----------------- [新增] 独立函数：计算恒星位置 -----------------
def calculate_fixed_stars(jd_utc, selected_stars, ecliptic_mode='tropical', ayanamsha_mode='SIDM_KRISHNAMURTI'):
    """
    计算给定儒略日下，一组恒星的位置。
    返回格式与 planet_positions 完全一致。

    参数：
        jd_utc         : 儒略日（直接从 calculate_positions 的返回值里取）
        selected_stars : 一个列表，每项是恒星名字字符串，例如 ['Sirius', 'Spica', 'Regulus']
        ecliptic_mode  : 黄道模式，与主计算保持一致
        ayanamsha_mode : 岁差体系，与主计算保持一致
    """
    # --- 第一步：根据黄道模式决定 flag ---
    # 这和 calculate_positions 里的逻辑完全一样
    if ecliptic_mode == 'sidereal':
        # 如果用的是恒星黄道，先把岁差模式设置好
        if isinstance(ayanamsha_mode, str):
            clean_name = ayanamsha_mode.replace("swe.", "").strip()
            if hasattr(swe, clean_name):
                swe.set_sid_mode(getattr(swe, clean_name))
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED
    else:
        flag = swe.FLG_SWIEPH | swe.FLG_SPEED

    # --- 第二步：循环计算每颗恒星 ---
    fixed_star_positions = {}

    for star_name in selected_stars:
        try:
            # 黄道坐标：调用 fixstar2_ut
            # 注意返回值是三个：(xx元组, 恒星完整名字, 返回码)
            # 这和 calc_ut 的两个返回值不同！
            xx, returned_name, ret_flag = swe.fixstar2_ut(star_name, jd_utc, flag)

            # 赤道坐标：加上 FLG_EQUATORIAL 标志位再调用一次
            xx_eq, _, _ = swe.fixstar2_ut(star_name, jd_utc, flag | swe.FLG_EQUATORIAL)

            # 存入字典，格式与 planet_positions 完全一致
            # 注意：恒星的 speed 和 dec_speed 极其接近 0，是正常现象
            fixed_star_positions[star_name] = {
                'lon':       xx[0] % 360,
                'lat':       xx[1],
                'speed':     xx[3],
                'ra':        xx_eq[0],
                'dec':       xx_eq[1],
                'dec_speed': xx_eq[4]
            }

        except Exception as e:
            # 如果某颗星名字写错了或找不到，跳过并打印提示，不影响其他星
            print(f"⚠️ 恒星 '{star_name}' 计算失败，已跳过。原因：{e}")
            continue

    return fixed_star_positions
# ----------------- [恒星函数结束] -----------------

# ----------------- [从 attributes.py 移入] 计算行星时 (Planetary Hour) -----------------
def get_planetary_hour(birth_config, sunrise_config):
    """
    计算当前时间对应的行星时 (Planetary Hour)。
    逻辑：根据日出日落将白天和黑夜各分12等分，起始星为值日星，按迦勒底序列顺推。
    """
    # 1. 基础配置与时间解析 (与日出函数类似)
    try:
        bundled_ephe_path = pkg_resources.resource_filename('quant_astro', 'ephe')
        swe.set_ephe_path(bundled_ephe_path)
    except Exception:
        pass 

    lat = _parse_dms(birth_config['latitude_str'])
    lon = _parse_dms(birth_config['longitude_str'])
    alt = birth_config.get('elevation', 0.0)
    tz_offset = _parse_timezone(birth_config['timezone_str'])
    
    local_dt_str = birth_config['local_time_str']
    calendar = birth_config.get('calendar', 'g')
    local_dt = _parse_local_time_and_convert_to_gregorian(local_dt_str, calendar)

    # 2. 定义辅助函数：计算特定日期的日出日落
    def calc_sun_events(target_date):
        """返回 target_date 当天的 (日出dt, 日落dt)"""
        # 构造 UTC 午夜
        midnight_local = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_utc = midnight_local - timedelta(hours=tz_offset)
        jd_start = swe.julday(midnight_utc.year, midnight_utc.month, midnight_utc.day,
                              midnight_utc.hour + midnight_utc.minute/60.0)
        
        geopos = (lon, lat, alt)
        press = birth_config.get('atpress', 1013.25)
        temp = birth_config.get('attemp', 10.0)
        # === [核心修改开始] 智能处理 RSMI 标志 ===
        # 1. 获取用户配置的原始标志 (默认为 RISE | CENTER)
        user_rsmi = sunrise_config.get('rsmi', swe.CALC_RISE | swe.BIT_DISC_CENTER)
        
        # 2. 剥离方向标志，只保留样式标志 (如 Center, Bottom, No Refraction)
        # 逻辑：(用户标志) AND (非 RISE) AND (非 SET)
        style_flags = user_rsmi & ~swe.CALC_RISE & ~swe.CALC_SET
        
        # 3. 重新组合出这一刻需要的标志
        flag_rise = swe.CALC_RISE | style_flags  # 强制叠加 RISE
        flag_set = swe.CALC_SET | style_flags    # 强制叠加 SET
        # === [核心修改结束] ===

        # 计算日出 (使用 flag_rise)
        res_rise = swe.rise_trans(jd_start, swe.SUN, flag_rise, geopos, press, temp, swe.FLG_SWIEPH)
        rise_jd = res_rise[1][0] if isinstance(res_rise[1], tuple) else res_rise[0][0] 
        
        # 计算日落 (使用 flag_set)
        res_set = swe.rise_trans(jd_start, swe.SUN, flag_set, geopos, press, temp, swe.FLG_SWIEPH)
        set_jd = res_set[1][0] if isinstance(res_set[1], tuple) else res_set[0][0]

        # JD 转 Local Datetime
        def jd_to_local(jd_val):
            y, m, d, h_dec = swe.revjul(jd_val)
            h = int(h_dec)
            mn = int((h_dec - h) * 60)
            s = (h_dec - h - mn/60) * 3600
            dt_utc = datetime(y, m, d, h, mn, int(s), int((s-int(s))*1000000))
            return dt_utc + timedelta(hours=tz_offset)

        return jd_to_local(rise_jd), jd_to_local(set_jd)

    # 3. 确定当前属于哪个"占星日"以及光照区间
    # 先算当天的日出日落
    rise_today, set_today = calc_sun_events(local_dt)
    
    is_day_time = False
    start_time = None
    end_time = None
    astrological_day_start = None # 用于确定值日星
    
    if local_dt < rise_today:
        # 情况A：还没日出 -> 属于"昨天"的夜间时段
        # 需要"昨天"的日落 和 "今天"的日出
        rise_prev, set_prev = calc_sun_events(local_dt - timedelta(days=1))
        
        is_day_time = False
        start_time = set_prev
        end_time = rise_today
        astrological_day_start = rise_prev # 昨天的日出决定了昨天的值日星
        
    elif local_dt >= set_today:
        # 情况B：已经日落 -> 属于"今天"的夜间时段
        # 需要"今天"的日落 和 "明天"的日出
        rise_next, set_next = calc_sun_events(local_dt + timedelta(days=1))
        
        is_day_time = False
        start_time = set_today
        end_time = rise_next
        astrological_day_start = rise_today # 今天的日出决定了值日星
        
    else:
        # 情况C：白天 -> 属于"今天"的日间时段
        is_day_time = True
        start_time = rise_today
        end_time = set_today
        astrological_day_start = rise_today

    # 4. 计算当前是第几个行星时
    total_duration = (end_time - start_time).total_seconds()
    elapsed = (local_dt - start_time).total_seconds()
    hour_length = total_duration / 12.0
    
    # 当前时序 index (0-11)
    hour_idx = int(elapsed / hour_length)
    if hour_idx >= 12: hour_idx = 11 # 防止精度误差导致溢出

    # 5. 推算行星
    # 迦勒底序列 (速度从慢到快: 土 -> 月)
    # 顺序: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon
    chaldean_order = ['Sa', 'Ju', 'Ma', 'Su', 'Ve', 'Me', 'Mo']
    
    # 计算值日星 (Day Lord)
    # weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    # 映射到 chaldean_order 的索引
    # Mon(Mo) -> index 6
    # Tue(Ma) -> index 2
    # Wed(Me) -> index 5
    # Thu(Ju) -> index 1
    # Fri(Ve) -> index 4
    # Sat(Sa) -> index 0
    # Sun(Su) -> index 3
    weekday_map = {0: 6, 1: 2, 2: 5, 3: 1, 4: 4, 5: 0, 6: 3}
    
    # 获取占星日的 weekday (根据日出时间判定的那天)
    astro_weekday = astrological_day_start.weekday()
    day_lord_idx = weekday_map[astro_weekday]
    
    # 核心公式
    # 如果是白天：从 Day Lord 开始数 hour_idx 个
    # 如果是晚上：从 Day Lord 开始数 12 个(白天的) + hour_idx 个(晚上的)
    # 简化：序列是循环的，所以直接加就行
    
    offset = hour_idx
    if not is_day_time:
        offset += 12 # 加上白天的12个小时
        
    final_idx = (day_lord_idx + offset) % 7
    planet_lord = chaldean_order[final_idx]

    return {
        'planetary_hour_lord': planet_lord, # 行星时主星
        'is_day_time': is_day_time,         # 是否为日间
        'hour_index': hour_idx + 1,         # 第几个行星时 (1-12)
        'hour_start': str(start_time + timedelta(seconds=hour_idx*hour_length)), # 当前行星时开始时间
        'hour_end': str(start_time + timedelta(seconds=(hour_idx+1)*hour_length)) # 当前行星时结束时间
    }
# ----------------- [行星时函数结束] -----------------
