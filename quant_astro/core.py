# quant_astro/core.py

import swisseph as swe
from datetime import datetime, timedelta
import pytz
import re

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
    node_mode='mean', house_system='Placidus', ephe_path='/usr/share/sweph/ephe'
):
    """
    计算给定时间和地点的行星和宫位位置。
    
    返回:
        一个元组，包含 (planet_positions, house_positions, jd_utc)
    """
    swe.set_ephe_path(ephe_path)

    # 1. 解析输入参数
    local_dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S.%f")
    latitude = _parse_dms(latitude_str)
    longitude = _parse_dms(longitude_str)
    timezone_offset = _parse_timezone(timezone_str)

    # 2. 计算儒略日 (Julian Day)
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
    planet_positions = {}
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
    house_codes = {'Placidus': b'P', 'Koch': b'K', 'Regiomontanus': b'R', 'Whole Sign': b'W', 'Equal': b'E', 'Campanus': b'C'}
    
    if house_system in house_codes:
        houses, ascmc = swe.houses_ex(jd_utc, latitude, longitude, house_codes[house_system], flags=house_flag)
        for i, cusp_lon in enumerate(houses[:12]):
            pos_ecl = (cusp_lon, 0.0, 1.0)
            pos_eq = swe.cotrans(pos_ecl, swe.FLG_EQUATORIAL)
            house_positions[f"house {i+1}"] = {'lon': cusp_lon % 360, 'lat': 0.0, 'ra': pos_eq[0], 'dec': pos_eq[1]}

    return planet_positions, house_positions, ascmc, jd_utc