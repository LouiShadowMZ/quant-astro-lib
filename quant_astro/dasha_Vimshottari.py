# quant_astro/dasha.py

from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pytz
import csv
import pkg_resources
import pandas as pd

# --- 内部辅助函数 ---

def _parse_timezone(tz_str):
    """解析时区字符串为小时浮点数 (从您的 notebook 中提取)"""
    import re
    match = re.match(r'^([+-]?)(\d{1,2})(:?)(\d{0,2})$', tz_str)
    if not match:
        raise ValueError(f"无法解析时区字符串: {tz_str}")
    sign = -1 if match.group(1) == '-' else 1
    hours = float(match.group(2))
    mins = float(match.group(4) or 0)
    return sign * (hours + mins/60)

def _calculate_e_seconds(moon_lon, days_in_year):
    """
    计算需要从出生时间中减去的总秒数 (E值)。
    对应您 notebook 中计算 E 的单元格。
    """
    getcontext().prec = 20 # 设置高精度
    
    # 1. 读取打包在库中的 star.csv 文件
    star_file_path = pkg_resources.resource_filename('quant_astro', 'data/star.csv')
    with open(star_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        star_data = [row for row in reader]

    # 2. 找到月亮所在的星宿区间
    lon = Decimal(str(moon_lon))
    moon_star_details = None
    for entry in star_data:
        from_deg = Decimal(entry['From'])
        to_deg = Decimal(entry['To'])
        # 处理0度的情况（Revati区间跨越360度）
        if from_deg > to_deg: # 例如从 346.66 到 360
            if lon >= from_deg or lon < to_deg:
                 moon_star_details = entry
                 break
        elif from_deg <= lon < to_deg:
            moon_star_details = entry
            break
            
    if not moon_star_details:
        raise ValueError("未能根据月亮经度找到对应的星宿区间。")

    # 3. 执行您在 notebook 中的一系列计算
    from_deg = Decimal(moon_star_details['From'])
    F = lon - from_deg if lon >= from_deg else (Decimal('360') + lon) - from_deg
    A = Decimal(str(days_in_year)) * Decimal('86400')
    B = Decimal(moon_star_details['YearNumber'])
    C = B * A
    D = C * F
    divisor = Decimal('13.333333333333334') # 13度20分转换成的小数
    E = D / divisor
    
    return E, moon_star_details['Star-Lord']

def _calculate_dasha_start_time(birth_time_str, timezone_str, e_seconds):
    """
    根据E值计算Dasha周期的起始时间。
    对应您 notebook 中计算初始日期的单元格。
    """
    getcontext().prec = 20
    
    # 1. 解析时间和时区
    initial_time = datetime.strptime(birth_time_str, "%Y-%m-%d %H:%M:%S.%f")
    timezone_offset = _parse_timezone(timezone_str)
    local_tz = pytz.FixedOffset(int(timezone_offset * 60))
    initial_utc = local_tz.localize(initial_time).astimezone(pytz.utc)
    
    # 2. 高精度时间减法
    total_seconds_to_subtract = Decimal(str(e_seconds))
    days, remainder_seconds = divmod(total_seconds_to_subtract, Decimal('86400'))
    seconds_int = int(remainder_seconds)
    microseconds = int((remainder_seconds - seconds_int) * 1_000_000)
    
    delta = timedelta(days=int(days), seconds=seconds_int, microseconds=microseconds)
    dasha_start_utc = initial_utc - delta
    
    return dasha_start_utc.astimezone(local_tz)

def _generate_dasha_intervals(dasha_start_time, first_lord, dasa_config):
    """
    生成所有层级的Dasha时间表。
    对应您 notebook 中最终生成层级划分的单元格。
    """
    getcontext().prec = 20
    
    # 1. 从配置中解包参数
    MAX_LEVEL = dasa_config.get("max_level", 4)
    OUTPUT_MODE = dasa_config.get("output_mode", "all")
    DAYS_IN_YEAR = dasa_config.get("days_in_year", 365.25)
    
    # 2. 行星周期定义 (与您的 notebook 保持一致)
    planet_cycle = {
        'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
        'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
        'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
        'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
        'Me': {'value': 17, 'next': 'Ke'}
    }
    
    A = Decimal(str(DAYS_IN_YEAR)) * Decimal('86400')
    planet_seconds = {p: Decimal(d['value']) * A for p, d in planet_cycle.items()}

    # 3. 递归函数 (与您的 notebook 保持一致，非常棒的设计！)
    def divide_interval(main_planet, start, end, level, max_level):
        intervals = []
        sub_periods_at_this_level = []
        current_planet = main_planet
        current_start = start
        parent_total_seconds = Decimal((end - start).total_seconds())

        for _ in range(9):
            planet_years = Decimal(planet_cycle[current_planet]['value'])
            sub_seconds = (parent_total_seconds * planet_years) / Decimal(120)
            current_end = current_start + timedelta(seconds=float(sub_seconds))
            sub_periods_at_this_level.append((f"L{level} {current_planet}", current_start, current_end))
            current_planet = planet_cycle[current_planet]['next']
            current_start = current_end
            
        intervals.extend(sub_periods_at_this_level)

        if level < max_level:
            for name, sub_start, sub_end in sub_periods_at_this_level:
                sub_main_planet = name.split()[-1]
                deeper_intervals = divide_interval(sub_main_planet, sub_start, sub_end, level + 1, max_level)
                intervals.extend(deeper_intervals)
        
        return intervals

    # 4. 主逻辑
    # 生成 Level 1
    level1_intervals = []
    current_time = dasha_start_time
    current_planet = first_lord
    for _ in range(9):
        seconds_to_add = planet_seconds[current_planet]
        end_time = current_time + timedelta(seconds=float(seconds_to_add))
        level1_intervals.append((f"L1 {current_planet}", current_time, end_time))
        current_time = end_time
        current_planet = planet_cycle[current_planet]['next']

    # 生成更深层级
    all_intervals = []
    if OUTPUT_MODE == 'all':
        all_intervals.extend(level1_intervals)
        
    for l1_name, l1_start, l1_end in level1_intervals:
        main_planet = l1_name.split()[-1]
        all_intervals.extend(divide_interval(main_planet, l1_start, l1_end, 2, MAX_LEVEL))

    # 排序并格式化为 DataFrame
    all_intervals.sort(key=lambda x: x[1])
    
    # 创建 DataFrame
    final_data = []
    for name, start, end in all_intervals:
        level, planet = name.split()
        final_data.append({
            'Level': int(level[1:]),
            'Planet': planet,
            'date': start.strftime('%Y-%m-%d %H:%M:%S.%f')
        })
        
    df = pd.DataFrame(final_data)

    # 根据 output_mode 筛选
    if OUTPUT_MODE == 'present':
        df = df[df['Level'] == MAX_LEVEL].reset_index(drop=True)
        
    return df