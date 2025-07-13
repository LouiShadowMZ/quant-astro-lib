# quant_astro/dasha.py

import csv
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pandas as pd
import pkg_resources
import pytz

# 导入您自己的核心计算模块
from .core import calculate_positions

# 尝试导入Colab的下载工具，如果失败则忽略（这样代码在本地也能运行）
try:
    from google.colab import files
    IS_COLAB = True
except ImportError:
    IS_COLAB = False

# ===================================================================
#  新的“一键生成”函数 (这是您将要调用的唯一函数)
# ===================================================================

def generate_dasha_report(
    local_time_str,
    timezone_str,
    ayanamsha_mode, # 岁差模式是必须的
    days_in_year=365.25,
    max_level=4,
    output_filename="dasha_report.csv",
    ephe_path=None,
    star_csv_path=None
):
    """
    一键生成并下载Vimshottari Dasha报告。
    这个函数会处理所有内部计算，您只需调用它一次。
    """
    print("🚀 开始生成大运报告...")
    
    # 1. 内部调用核心函数计算行星位置
    # 注意：大运计算只需要月亮经度，不需要地理位置等参数
    print("   - 步骤 1/4: 计算月亮精确位置...")
    planet_pos, _, _, _ = calculate_positions(
        local_time_str=local_time_str,
        timezone_str=timezone_str,
        # 对于大运计算，以下参数可以写死，因为它们不影响月亮经度
        latitude_str="0°0'0.00\"",
        longitude_str="0°0'0.00\"",
        elevation=0,
        ecliptic_mode='sidereal', # 大运总是基于恒星黄道
        ayanamsha_mode=ayanamsha_mode,
        ephe_path=ephe_path
    )
    moon_longitude = planet_pos['Mo']['lon']
    print(f"   - 月亮经度计算完成: {moon_longitude:.4f}°")

    # 2. 内部调用大运计算函数
    print("   - 步骤 2/4: 计算大运时间区间...")
    dasha_periods = _calculate_dasha_periods(
        moon_lon=moon_longitude,
        local_time_str=local_time_str,
        timezone_str=timezone_str,
        days_in_year=days_in_year,
        max_level=max_level,
        star_csv_path=star_csv_path
    )
    print("   - 大运时间计算完成。")

    # 3. 生成CSV文件
    print("   - 步骤 3/4: 生成CSV文件...")
    with open(output_filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Level", "Planet", "Start Date (UTC)"]) # 写入文件头
        for name, start, _ in dasha_periods:
            level_planet = name.split()
            level = level_planet[0][1:]
            planet = level_planet[1]
            # 使用ISO格式并包含时区信息
            start_str = start.strftime('%Y-%m-%d %H:%M:%S.%f%z')
            writer.writerow([level, planet, start_str])
    print(f"   - 文件 '{output_filename}' 已生成。")

    # 4. 触发浏览器下载（仅在Colab环境中）
    if IS_COLAB:
        print("   - 步骤 4/4: 触发浏览器下载...")
        files.download(output_filename)
        print("\n✅ 报告生成完毕，文件已开始下载！")
    else:
        print(f"\n✅ 报告生成完毕！文件已保存在当前目录: {output_filename}")


# ===================================================================
#  内部使用的函数 (这些函数由上面的总管函数调用，您无需关心)
# ===================================================================

def _calculate_dasha_periods(
    moon_lon, local_time_str, timezone_str,
    days_in_year, max_level, star_csv_path
):
    """
    (内部函数) 计算Vimshottari Dasha大运周期。
    """
    if star_csv_path is None:
        star_csv_path = pkg_resources.resource_filename('quant_astro', 'data/star.csv')
        
    star_lord, E_seconds = _get_dasha_balance(moon_lon, star_csv_path, days_in_year)
    
    # 时间处理
    initial_time = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M:%S.%f")
    
    # 解析时区
    match = pytz.re.match(r'^([+-])(\d{1,2}):?(\d{2})?$', timezone_str)
    if match:
        sign, hours, minutes = match.groups('0')
        offset_minutes = int(hours) * 60 + int(minutes)
        if sign == '-':
            offset_minutes = -offset_minutes
        local_tz = pytz.FixedOffset(offset_minutes)
    else: # 支持像 "+8" 这样的简单格式
        offset = int(float(timezone_str) * 60)
        local_tz = pytz.FixedOffset(offset)

    initial_utc = local_tz.localize(initial_time).astimezone(pytz.utc)
    dasha_start_utc = _subtract_seconds(initial_utc, E_seconds)
    
    planet_cycle = {
        'Ke': {'value': 7, 'next': 'Ve'}, 'Ve': {'value': 20, 'next': 'Su'},
        'Su': {'value': 6, 'next': 'Mo'}, 'Mo': {'value': 10, 'next': 'Ma'},
        'Ma': {'value': 7, 'next': 'Ra'}, 'Ra': {'value': 18, 'next': 'Ju'},
        'Ju': {'value': 16, 'next': 'Sa'}, 'Sa': {'value': 19, 'next': 'Me'},
        'Me': {'value': 17, 'next': 'Ke'}
    }
    
    A = Decimal(str(days_in_year)) * Decimal('86400')
    planet_seconds = {p: Decimal(d['value']) * A for p, d in planet_cycle.items()}

    level1_intervals = []
    start_time = dasha_start_utc
    current_planet = star_lord
    
    for _ in range(9):
        end_time = _add_seconds(start_time, planet_seconds[current_planet])
        level1_intervals.append((f"L1 {current_planet}", start_time, end_time))
        start_time = end_time
        current_planet = planet_cycle[current_planet]['next']

    all_intervals = list(level1_intervals)
    if max_level > 1:
        for l1_name, l1_start, l1_end in level1_intervals:
            main_planet = l1_name.split()[-1]
            all_intervals.extend(_divide_interval_recursive(main_planet, l1_start, l1_end, 2, max_level, planet_cycle))
            
    all_intervals.sort(key=lambda x: x[1])
    return all_intervals

def _get_dasha_balance(moon_lon, star_data_path, days_in_year):
    """(内部函数) 计算大运的初始剩余时间"""
    getcontext().prec = 20
    df = pd.read_csv(star_data_path, dtype={'From': str, 'To': str, 'YearNumber': str})
    
    moon_lon_dec = Decimal(str(moon_lon))
    
    moon_star_row = None
    for _, row in df.iterrows():
        from_deg = Decimal(row['From'])
        to_deg = Decimal(row['To']) if Decimal(row['To']) != Decimal('0') else Decimal('360')
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
    B = Decimal(moon_star_row['YearNumber'])
    C = B * A
    D = C * F
    E = D / Decimal('13.333333333333334')

    return star_lord, E

def _divide_interval_recursive(main_planet, start, end, level, max_level, planet_cycle):
    """(内部函数) 递归划分时间区间"""
    if level > max_level: return []
    
    intervals = []
    current_planet, current_start = main_planet, start
    total_seconds = Decimal((end - start).total_seconds())
    
    for _ in range(9):
        planet_years = Decimal(planet_cycle[current_planet]['value'])
        sub_seconds = (total_seconds * planet_years) / Decimal(120)
        current_end = current_start + timedelta(seconds=float(sub_seconds))
        intervals.append((f"L{level} {current_planet}", current_start, current_end))
        current_planet, current_start = planet_cycle[current_planet]['next'], current_end

    if level < max_level:
        deeper_intervals = []
        for name, sub_start, sub_end in intervals:
            deeper_intervals.extend(_divide_interval_recursive(name.split()[-1], sub_start, sub_end, level + 1, max_level, planet_cycle))
        intervals.extend(deeper_intervals)
        
    return intervals

def _add_seconds(dt, seconds):
    """(内部函数) 高精度时间加法"""
    total_seconds = Decimal(str(seconds))
    days, remainder_seconds = divmod(total_seconds, Decimal('86400'))
    seconds_int, microseconds = int(remainder_seconds), int((remainder_seconds - int(remainder_seconds)) * 1_000_000)
    return dt + timedelta(days=int(days), seconds=seconds_int, microseconds=microseconds)

def _subtract_seconds(dt, seconds):
    """(内部函数) 高精度时间减法"""
    return _add_seconds(dt, -Decimal(str(seconds)))