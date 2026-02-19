# quant_astro/attributes.py

import swisseph as swe
from datetime import datetime, timedelta
import re
import pkg_resources

# --- 常量定义 ---
ZODIAC_NAMES = ['Ari', 'Tau', 'Gem', 'Cnc', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqr', 'Pis']

# 古典占星/KP/吠陀占星 守护星映射 (Traditional Rulership)
# 0=Ari(Ma), 1=Tau(Ve), 2=Gem(Me), 3=Cnc(Mo), 4=Leo(Su), 5=Vir(Me)
# 6=Lib(Ve), 7=Sco(Ma), 8=Sag(Ju), 9=Cap(Sa), 10=Aqr(Sa), 11=Pis(Ju)
SIGN_LORDS_MAP = {
    0: 'Ma', 1: 'Ve', 2: 'Me', 3: 'Mo', 4: 'Su', 5: 'Me',
    6: 'Ve', 7: 'Ma', 8: 'Ju', 9: 'Sa', 10: 'Sa', 11: 'Ju'
}

# --- 辅助工具 (私有) ---
def _parse_dms(dms_str):
    parts = re.findall(r"[\d.]+", dms_str)
    return float(parts[0]) + float(parts[1])/60 + float(parts[2])/3600

def _parse_timezone(tz_str):
    match = re.match(r'^([+-]?)(\d{1,2})(:?)(\d{0,2})$', tz_str)
    sign = -1 if match.group(1) == '-' else 1
    hours = float(match.group(2))
    mins = float(match.group(4) or 0)
    return sign * (hours + mins/60)

def _get_sign_info(lon_decimal):
    """根据黄经计算星座和度数"""
    idx = int(lon_decimal / 30) % 12
    lon_in_sign = lon_decimal % 30
    return {
        'sign': ZODIAC_NAMES[idx],
        'lon': lon_in_sign,
        'idx': idx # 保留索引方便后续计算主宰星
    }

# --- 主功能函数 ---

def get_attributes(planet_positions, house_positions):
    """
    接收原始的行星和宫位位置字典，返回占星属性字典。
    
    Returns:
        tuple: (planet_signs, house_signs, planet_houses, house_lords)
    """
    
    # 字典 1: 行星的星座归属
    planet_signs = {
        k: _get_sign_info(v['lon']) 
        for k, v in planet_positions.items()
    }

    # 字典 2: 宫位的星座归属
    house_signs = {
        k: _get_sign_info(v['lon']) 
        for k, v in house_positions.items()
    }

    # 字典 4: 每个宫位的主宰星 (根据宫头星座)
    house_lords = {}
    for h_key, h_info in house_signs.items():
        sign_idx = h_info['idx']
        lord = SIGN_LORDS_MAP.get(sign_idx, 'Unknown')
        house_lords[h_key] = lord

    # 字典 3: 行星的宫位归属 (计算行星落在哪个宫)
    # 逻辑：比较行星黄经与宫头黄经
    planet_houses = {}
    
    # 提取宫头列表并排序 (1-12宫)
    # 格式: [(1, 23.5), (2, 54.2), ...]
    cusps = []
    for i in range(1, 13):
        h_name = f"house {i}"
        if h_name in house_positions:
            cusps.append((i, house_positions[h_name]['lon']))
            
    # 如果没有足够的宫位数据，跳过
    if len(cusps) == 12:
        for p_name, p_data in planet_positions.items():
            p_lon = p_data['lon']
            located_house = None
            
            for i in range(12):
                curr_h, curr_lon = cusps[i]
                next_h, next_lon = cusps[(i + 1) % 12] # 循环回到第1宫
                
                # 处理跨越 360/0 度的情况 (例如 12宫头在 350度, 1宫头在 20度)
                if next_lon < curr_lon: 
                    if p_lon >= curr_lon or p_lon < next_lon:
                        located_house = curr_h
                        break
                else:
                    # 正常情况 (例如 1宫头 20度, 2宫头 50度)
                    if curr_lon <= p_lon < next_lon:
                        located_house = curr_h
                        break
            
            planet_houses[p_name] = located_house
            
    return planet_signs, house_signs, planet_houses, house_lords


# --- [移植] 日出与值日星计算 ---
def get_sun_rise_and_lord(birth_config, sunrise_config):
    """
    独立计算日出时间及值日星 (从 core.py 移植)
    """
    # 确保路径设置 (防呆)
    try:
        bundled_ephe_path = pkg_resources.resource_filename('quant_astro', 'ephe')
        swe.set_ephe_path(bundled_ephe_path)
    except Exception:
        pass 

    lat = _parse_dms(birth_config['latitude_str'])
    lon = _parse_dms(birth_config['longitude_str'])
    alt = birth_config.get('elevation', 0.0)
    
    local_dt_str = birth_config['local_time_str']
    try:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S")

    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    tz_offset = _parse_timezone(birth_config['timezone_str'])
    utc_midnight = local_midnight - timedelta(hours=tz_offset)
    
    jd_start = swe.julday(utc_midnight.year, utc_midnight.month, utc_midnight.day,
                          utc_midnight.hour + utc_midnight.minute/60.0 + utc_midnight.second/3600.0)

    press = birth_config.get('atpress', 1013.25) 
    temp = birth_config.get('attemp', 10.0)  
    rsmi = sunrise_config.get('rsmi', swe.CALC_RISE | swe.BIT_DISC_CENTER)
    
    try:
        geopos = (lon, lat, alt)
        res = swe.rise_trans(jd_start, swe.SUN, rsmi, geopos, press, temp, swe.FLG_SWIEPH)
        
        rise_jd = 0.0
        ret_flag = -1
        
        if isinstance(res, tuple):
            if isinstance(res[0], int) and len(res) > 1 and isinstance(res[1], tuple):
                ret_flag = res[0]
                rise_jd = res[1][0]
            elif isinstance(res[0], tuple) and len(res) > 1 and isinstance(res[1], int):
                ret_flag = res[1]
                rise_jd = res[0][0]
            elif isinstance(res[0], float):
                ret_flag = 0
                rise_jd = res[0]
        
        if ret_flag < 0 or rise_jd <= 1.0: 
            return {'error': f"Sunrise not found. Flag={ret_flag}, JD={rise_jd}."}
            
    except swe.Error as e:
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
        return {'error': f"Date Conversion Error: {e}"}

    current_iso_weekday = local_dt.weekday() # 0=Mon
    
    if local_dt < rise_dt_local:
        effective_weekday = (current_iso_weekday - 1) % 7
    else:
        effective_weekday = current_iso_weekday

    chaldean_map = { 0: 'Mo', 1: 'Ma', 2: 'Me', 3: 'Ju', 4: 'Ve', 5: 'Sa', 6: 'Su' }
    
    return {
        'sunrise_time_local': str(rise_dt_local),
        'day_lord': chaldean_map.get(effective_weekday, 'Unknown'),
        'is_before_sunrise': local_dt < rise_dt_local
    }

# ----------------- [新增] 计算行星时 (Planetary Hour) -----------------
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
    try:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S")

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

    # 3. 确定当前属于哪个“占星日”以及光照区间
    # 先算当天的日出日落
    rise_today, set_today = calc_sun_events(local_dt)
    
    is_day_time = False
    start_time = None
    end_time = None
    astrological_day_start = None # 用于确定值日星
    
    if local_dt < rise_today:
        # 情况A：还没日出 -> 属于“昨天”的夜间时段
        # 需要“昨天”的日落 和 “今天”的日出
        rise_prev, set_prev = calc_sun_events(local_dt - timedelta(days=1))
        
        is_day_time = False
        start_time = set_prev
        end_time = rise_today
        astrological_day_start = rise_prev # 昨天的日出决定了昨天的值日星
        
    elif local_dt >= set_today:
        # 情况B：已经日落 -> 属于“今天”的夜间时段
        # 需要“今天”的日落 和 “明天”的日出
        rise_next, set_next = calc_sun_events(local_dt + timedelta(days=1))
        
        is_day_time = False
        start_time = set_today
        end_time = rise_next
        astrological_day_start = rise_today # 今天的日出决定了值日星
        
    else:
        # 情况C：白天 -> 属于“今天”的日间时段
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