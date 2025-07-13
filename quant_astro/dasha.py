# quant_astro/dasha.py

from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pandas as pd
import pkg_resources
import pytz

# --- 内部辅助函数 ---

def _add_seconds(dt, seconds):
    """高精度时间加法"""
    total_seconds = Decimal(str(seconds))
    days, remainder_seconds = divmod(total_seconds, Decimal('86400'))
    seconds_int = int(remainder_seconds)
    microseconds = int((remainder_seconds - seconds_int) * 1_000_000)
    delta = timedelta(days=int(days), seconds=seconds_int, microseconds=microseconds)
    return dt + delta

def _subtract_seconds(dt, seconds):
    """高精度时间减法"""
    total_seconds = Decimal(str(seconds))
    return _add_seconds(dt, -total_seconds)

def _get_dasha_balance(moon_lon, star_data_path, days_in_year):
    """计算大运的初始剩余时间"""
    getcontext().prec = 20 # 设置高精度
    df = pd.read_csv(star_data_path, dtype={'From': str, 'To': str})
    
    moon_lon_dec = Decimal(str(moon_lon))
    
    moon_star_row = None
    for _, row in df.iterrows():
        from_deg = Decimal(row['From'])
        to_deg = Decimal(row['To'])
        if to_deg == Decimal('0'):
            to_deg = Decimal('360')
        
        if from_deg <= moon_lon_dec < to_deg:
            moon_star_row = row
            break
            
    if moon_star_row is None:
        raise ValueError("无法找到月亮所在的星宿区间")

    star_lord = moon_star_row['Star-Lord']
    from_deg = Decimal(moon_star_row['From'])
    F = moon_lon_dec - from_deg
    days_in_year_dec = Decimal(str(days_in_year))
    A = days_in_year_dec * Decimal('86400')
    B = Decimal(str(moon_star_row['YearNumber']))
    C = B * A
    D = C * F
    E = D / Decimal('13.333333333333334') # 星宿一度的长度

    return star_lord, E

# --- 公开的核心函数 ---

def calculate_dasha_periods(
    moon_lon, local_time_str, timezone_str, 
    days_in_year=365.25, max_level=4, star_csv_path=None
):
    """
    计算Vimshottari Dasha大运周期。
    
    参数:
    - moon_lon (float): 月亮的恒星黄道经度。
    - local_time_str (str): 本地出生时间字符串。
    - timezone_str (str): 时区字符串。
    - days_in_year (float): 一年的天数定义。
    - max_level (int): 要计算的大运层级。
    - star_csv_path (str, optional): 自定义star.csv文件路径。如果为None，则使用库自带文件。
    
    返回:
    - all_intervals (list): 一个包含所有大运区间的列表。
    """
    if star_csv_path is None:
        star_csv_path = pkg_resources.resource_filename('quant_astro', 'data/star.csv')
        
    star_lord, E_seconds = _get_dasha_balance(moon_lon, star_csv_path, days_in_year)
    
    # 时间处理
    initial_time = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S.%f")
    # 注意：这里的时区解析逻辑需要和core.py保持一致，您可以从core.py导入_parse_timezone
    # 为简化，这里直接使用pytz
    match = pytz.re.match(r'^([+-])(\d{1,2}):?(\d{2})?$', timezone_str)
    sign, hours, minutes = match.groups('0')
    offset_minutes = int(hours) * 60 + int(minutes)
    if sign == '-':
        offset_minutes = -offset_minutes
    local_tz = pytz.FixedOffset(offset_minutes)
    
    initial_utc = local_tz.localize(initial_time).astimezone(pytz.utc)
    dasha_start_utc = _subtract_seconds(initial_utc, E_seconds)
    
    # 行星周期定义
    planet_cycle = {
        'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
        'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
        'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
        'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
        'Me': {'value': 17, 'next': 'Ke'}
    }
    
    A = Decimal(str(days_in_year)) * Decimal('86400')
    planet_seconds = {p: Decimal(d['value']) * A for p, d in planet_cycle.items()}

    # 生成Level 1
    level1_intervals = []
    start_time = dasha_start_utc
    current_planet = star_lord
    
    for _ in range(9):
        end_time = _add_seconds(start_time, planet_seconds[current_planet])
        level1_intervals.append((f"L1 {current_planet}", start_time, end_time))
        start_time = end_time
        current_planet = planet_cycle[current_planet]['next']

    # 递归生成子层级
    all_intervals = list(level1_intervals)
    for l1_name, l1_start, l1_end in level1_intervals:
        main_planet = l1_name.split()[-1]
        all_intervals.extend(_divide_interval_recursive(main_planet, l1_start, l1_end, 2, max_level, planet_cycle))
        
    all_intervals.sort(key=lambda x: x[1])
    return all_intervals

def _divide_interval_recursive(main_planet, start, end, level, max_level, planet_cycle):
    """内部递归函数，用于划分时间区间"""
    if level > max_level:
        return []
        
    intervals = []
    current_planet = main_planet
    current_start = start
    total_seconds = Decimal((end - start).total_seconds())
    
    for _ in range(9):
        planet_years = Decimal(planet_cycle[current_planet]['value'])
        sub_seconds = (total_seconds * planet_years) / Decimal(120)
        current_end = current_start + timedelta(seconds=float(sub_seconds))
        intervals.append((f"L{level} {current_planet}", current_start, current_end))
        current_planet = planet_cycle[current_planet]['next']
        current_start = current_end

    if level < max_level:
        deeper_intervals = []
        for name, sub_start, sub_end in intervals:
            sub_main_planet = name.split()[-1]
            deeper_intervals.extend(_divide_interval_recursive(sub_main_planet, sub_start, sub_end, level + 1, max_level, planet_cycle))
        intervals.extend(deeper_intervals)
        
    return intervals