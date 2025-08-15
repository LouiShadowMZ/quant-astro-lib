# quant_astro/core.py

import swisseph as swe
from datetime import datetime, timedelta
import pytz
import re
import pkg_resources
import pandas as pd

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
    ecliptic_mode='sidereal', ayanamsha_mode=swe.SIDM_KRISHNAMURTI_VP291,
    node_mode='mean', house_system='Placidus', ephe_path=None, 
    **kwargs
):
    """
    计算给定时间和地点的行星和宫位位置。
    如果提供了 ephe_path，则使用它。否则，使用库内置的星历文件。
    """
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
        swe.set_sid_mode(ayanamsha_mode)
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED
        house_flag = swe.FLG_SIDEREAL
    else:
        flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        house_flag = 0

    # 4. 计算行星位置
    # planet_positions = {}
    # node_flag = swe.TRUE_NODE if node_mode == 'true' else swe.MEAN_NODE
    # planet_map = {
    #     swe.SUN: 'Su', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve',
    #     swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur',
    #     swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl', node_flag: 'Ra'
    # }


    # 首先，根据是否启用日心制，准备好计算标志和行星列表
    flag_planets = swe.FLG_SWIEPH | swe.FLG_SPEED
    if ecliptic_mode == 'sidereal':
        flag_planets |= swe.FLG_SIDEREAL

    planet_positions = {}

    # 从kwargs中安全地获取日心制开关的值，如果找不到，则默认为False
    is_heliocentric = kwargs.get("USE_HELIOCENTRIC", False)
    
    if is_heliocentric:
        print("☀️ 已切换到日心制行星计算模式...")
        # 为计算标志增加日心制 flag
        flag_planets |= swe.FLG_HELCTR
        
        # 定义日心制的行星列表 (包含地球，不含太阳、月亮和交点)
        planet_map = {
            swe.EARTH: 'Ea', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve', swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur', swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl'
        }
    else: # 默认使用地心制
        # 定义地心制的行星列表 (包含太阳、月亮和交点)
        node_flag = swe.TRUE_NODE if node_mode == 'true' else swe.MEAN_NODE
        planet_map = {
            swe.SUN: 'Su', swe.MOON: 'Mo', swe.MERCURY: 'Me', swe.VENUS: 'Ve',
            swe.MARS: 'Ma', swe.JUPITER: 'Ju', swe.SATURN: 'Sa', swe.URANUS: 'Ur',
            swe.NEPTUNE: 'Ne', swe.PLUTO: 'Pl', node_flag: 'Ra'
        }

    for p_id, name in planet_map.items():
        xx, _ = swe.calc_ut(jd_utc, p_id, flag)
        xx_eq, _ = swe.calc_ut(jd_utc, p_id, flag | swe.FLG_EQUATORIAL)
        planet_positions[name] = {'lon': xx[0] % 360, 'lat': xx[1], 'speed': xx[3], 'ra': xx_eq[0], 'dec': xx_eq[1]}
        
        if p_id == node_flag:
            south_lon = (xx[0] + 180) % 360
            south_lat = -xx[1]
            pos_ecl_south = (south_lon, south_lat, xx[2])
            pos_eq_south = swe.cotrans(pos_ecl_south, swe.FLG_EQUATORIAL)
            planet_positions['Ke'] = {'lon': south_lon, 'lat': south_lat, 'speed': xx[3], 'ra': pos_eq_south[0], 'dec': pos_eq_south[1]}

    # 5. 计算宫位位置
    house_positions = {}
    house_codes = {'Placidus': b'P', 'Koch': b'K', 'Regiomontanus': b'R', 'Whole Sign': b'W', 'Equal': b'E', 'Campanus': 'C'}
    
    if house_system in house_codes:
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

        houses, ascmc = swe.houses_ex(jd_for_houses, latitude, longitude, house_codes[house_system], flags=house_flag)
        
        for i, cusp_lon in enumerate(houses[:12]):
            pos_ecl = (cusp_lon, 0.0, 1.0)
            pos_eq = swe.cotrans(pos_ecl, swe.FLG_EQUATORIAL)
            house_positions[f"house {i+1}"] = {'lon': cusp_lon % 360, 'lat': 0.0, 'ra': pos_eq[0], 'dec': pos_eq[1]}

    return planet_positions, house_positions, ascmc, jd_utc