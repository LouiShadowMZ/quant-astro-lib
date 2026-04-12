# quant_astro/core.py

import swisseph as swe
from datetime import datetime, timedelta
import pytz
import re
import pkg_resources
import pandas as pd

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
    parts = re.findall(r"[\d.]+", dms_str)
    return float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600

def _parse_timezone(tz_str):
    match = re.match(r'^([+-]?)(\d{1,2})(:?)(\d{0,2})$', tz_str)
    sign = -1 if match.group(1) == '-' else 1
    hours = float(match.group(2))
    mins = float(match.group(4) or 0)
    return sign * (hours + mins/60)

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

    # 1. 解析输入参数 (这部分逻辑不变)
    local_dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S.%f")
    latitude = _parse_dms(latitude_str)
    longitude = _parse_dms(longitude_str)
    timezone_offset = _parse_timezone(timezone_str)

    # 2. 计算儒略日 (Julian Day) (这部分逻辑不变)
    utc_time = local_dt - timedelta(hours=timezone_offset)
    jd_utc = swe.julday(utc_time.year, utc_time.month, utc_time.day,
                       utc_time.hour + utc_time.minute/60 + utc_time.second/3600)

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
    planet_map = {
        swe.SUN: 'Su', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve',
        swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur',
        swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl', node_flag: 'Ra'
    }

    # 获取用户选择的行星列表，如果未提供则默认为 None (即全选)
    selected_planets = kwargs.get('selected_planets', None)

    for p_id, name in planet_map.items():
        # --- 过滤逻辑：判断是否需要计算该星体 ---
        should_calc = False
        if selected_planets is None or 'All' in selected_planets:
            should_calc = True
        else:
            # 如果是列表中的普通行星，则计算
            if name in selected_planets:
                should_calc = True
            # 特殊逻辑：如果是交点(Ra/Ke)，只要列表里有 Ra 或 Ke 任意一个，就必须进行核心计算
            if p_id == node_flag and ('Ra' in selected_planets or 'Ke' in selected_planets):
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
                pos_eq_south = swe.cotrans(pos_ecl_south, swe.FLG_EQUATORIAL)
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
            pos_eq = swe.cotrans(pos_ecl, swe.FLG_EQUATORIAL)
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
    
    return planet_positions, house_positions, ascmc, jd_utc, dignity_results


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
    try:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S")

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