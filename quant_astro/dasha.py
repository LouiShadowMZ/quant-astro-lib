# quant_astro/dasha.py

import pandas as pd
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pkg_resources
import os

# --- 初始化和配置 ---
# 【精度修正】将精度设为 20，与您原始 Notebook 完全一致
getcontext().prec = 20

# 行星周期定义 (不变)
PLANET_CYCLE = {
    'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
    'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
    'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
    'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
    'Me': {'value': 17, 'next': 'Ke'}
}

# --- 【核心修正】创建高精度的时间加减辅助函数 ---
def _add_decimal_seconds(dt, seconds_decimal):
    """
    一个高精度的时间加/减法函数，全程使用 Decimal 避免精度损失。
    """
    total_seconds = Decimal(seconds_decimal)
    
    # 检查是加法还是减法
    sign = 1 if total_seconds >= 0 else -1
    total_seconds = abs(total_seconds)

    # 将 Decimal 秒数分解成整数部分，用于 timedelta
    days = int(total_seconds // 86400)
    remainder_seconds = total_seconds % 86400
    seconds_int = int(remainder_seconds)
    microseconds = int((remainder_seconds - seconds_int) * 1_000_000)

    delta = timedelta(days=days, seconds=seconds_int, microseconds=microseconds)

    if sign == 1:
        return dt + delta
    else:
        return dt - delta

# --- 核心递归函数 (已修正) ---
def _divide_interval(main_planet, start, end, level, max_level):
    intervals = []
    sub_periods_at_this_level = []
    current_planet = main_planet
    current_start = start
    # total_seconds() 返回的是 float，我们必须用 Decimal 重新精确计算
    parent_total_seconds = Decimal((end - start).days * 86400) + Decimal((end - start).seconds) + Decimal((end - start).microseconds) / Decimal(1_000_000)

    for _ in range(9):
        planet_years = Decimal(PLANET_CYCLE[current_planet]['value'])
        sub_seconds = (parent_total_seconds * planet_years) / Decimal(120)
        # 【精度修正】使用我们新的高精度时间函数
        current_end = _add_decimal_seconds(current_start, sub_seconds)
        sub_periods_at_this_level.append((f"L{level} {current_planet}", current_start, current_end))
        current_planet = PLANET_CYCLE[current_planet]['next']
        current_start = current_end
    
    intervals.extend(sub_periods_at_this_level)

    if level < max_level:
        for name, sub_start, sub_end in sub_periods_at_this_level:
            sub_main_planet = name.split()[-1]
            deeper_intervals = _divide_interval(sub_main_planet, sub_start, sub_end, level + 1, max_level)
            intervals.extend(deeper_intervals)
            
    return intervals

# --- 主功能函数 (已修正) ---
def generate_dasha_table(moon_lon, birth_datetime, days_in_year, max_level, output_mode):
    # 1. 读取库内自带的 star.csv 文件 (不变)
    star_csv_path = pkg_resources.resource_filename('quant_astro', 'data/star.csv')
    star_data = pd.read_csv(star_csv_path, dtype={'From': str, 'To': str, 'YearNumber': str})

    # 2. 找到月亮所在的星宿 (不变)
    moon_star_row = None
    for _, row in star_data.iterrows():
        from_deg = Decimal(row['From'])
        to_deg = Decimal(row['To'])
        if from_deg <= Decimal(moon_lon) < to_deg:
            moon_star_row = row
            break
    if moon_star_row is None:
        raise ValueError("无法在 star.csv 中找到对应的月亮位置。")

    # 3. 计算 Dasha 周期的起始时间 (不变, 因为这里已经是 Decimal)
    f_val = Decimal(moon_lon) - Decimal(moon_star_row['From'])
    b_val = Decimal(moon_star_row['YearNumber'])
    c_val = b_val * Decimal(days_in_year) * Decimal("86400")
    d_val = c_val * f_val
    e_seconds = d_val / Decimal("13.333333333333333333") # 维持高精度
    
    # 【精度修正】使用我们新的高精度时间函数
    dasha_start_time = _add_decimal_seconds(birth_datetime, -e_seconds)

    # 4. 计算 L1 (大运) 周期
    planet_seconds = {p: Decimal(d['value']) * Decimal(days_in_year) * Decimal("86400") for p, d in PLANET_CYCLE.items()}
    
    level1_intervals = []
    start_time = dasha_start_time
    current_lord = moon_star_row['Star-Lord']
    
    # 【精度修正】所有 timedelta 计算都使用高精度辅助函数
    end_time = _add_decimal_seconds(start_time, planet_seconds[current_lord])
    level1_intervals.append((f"L1 {current_lord}", start_time, end_time))
    
    start_time = end_time
    next_lord = PLANET_CYCLE[current_lord]['next']
    for _ in range(8):
        end_time = _add_decimal_seconds(start_time, planet_seconds[next_lord])
        level1_intervals.append((f"L1 {next_lord}", start_time, end_time))
        start_time = end_time
        next_lord = PLANET_CYCLE[next_lord]['next']

    # 5 & 6 & 7. 后面逻辑不变
    deeper_intervals_all = []
    for l1_name, l1_start, l1_end in level1_intervals:
        main_planet = l1_name.split()[-1]
        deeper_intervals_all.extend(_divide_interval(main_planet, l1_start, l1_end, 2, max_level))

    all_intervals = []
    if output_mode == 'all':
        all_intervals.extend(level1_intervals)
    all_intervals.extend(deeper_intervals_all)
    all_intervals.sort(key=lambda x: x[1])

    output_data = []
    for name, start, _ in all_intervals:
        parts = name.split()
        level = parts[0][1:]
        planet = parts[1]
        output_data.append({'Level': level, 'Planet': planet, 'Date': start.strftime('%Y-%m-%d %H:%M:%S.%f')})
        
    return pd.DataFrame(output_data)