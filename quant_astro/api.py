# quant_astro/api.py

from .dasha import _calculate_e_seconds, _calculate_dasha_start_time, _generate_dasha_intervals
from IPython.display import display, FileLink
import pandas as pd
import os

def create_dasha_table(planet_positions, birth_config, dasa_config):
    """
    一键生成Dasha表并提供下载链接。
    这是您库的主要入口函数。

    Args:
        planet_positions (dict): 从 core.py 的 calculate_positions 函数获取的行星位置字典。
        birth_config (dict): 包含出生信息的字典。
        dasa_config (dict): 包含Dasha计算设置的字典。
    """
    print("🚀 Dasha 表生成开始...")

    # 1. 从输入中提取必要信息
    # 遵循您的要求，直接从预先计算好的 planet_positions 字典中获取月亮经度
    try:
        moon_lon = planet_positions['Mo']['lon']
        print(f"✅ 成功获取月亮经度: {moon_lon:.4f}°")
    except KeyError:
        raise ValueError("输入的 'planet_positions' 字典中缺少 'Mo' (月亮) 的数据。")
    
    birth_time_str = birth_config["local_time_str"]
    timezone_str = birth_config["timezone_str"]
    days_in_year = dasa_config["days_in_year"]

    # 2. 调用 dasha.py 中的函数，分步执行计算
    print("⏳ 正在计算 Dasha 周期的起始时间...")
    e_seconds, first_lord = _calculate_e_seconds(moon_lon, days_in_year)
    print(f" - 起始主星 (First Lord): {first_lord}")
    print(f" - 计算出的偏移秒数 (E): {e_seconds:.4f}")
    
    dasha_start_time = _calculate_dasha_start_time(birth_time_str, timezone_str, e_seconds)
    print(f"✅ Dasha 周期起始本地时间: {dasha_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

    # 3. 生成 Dasha 表格数据
    print("⏳ 正在生成所有层级的 Dasha 时间点...")
    dasha_df = _generate_dasha_intervals(dasha_start_time, first_lord, dasa_config)
    print(f"✅ 成功生成 {len(dasha_df)} 条 Dasha 记录。")

    # 4. 保存为CSV并生成下载链接
    output_filename = "dasha_table.csv"
    dasha_df.to_csv(output_filename, index=False, encoding='utf-8')
    print(f"📄 CSV文件 '{output_filename}' 已保存到当前工作目录。")

    # 使用 IPython.display.FileLink 为 Jupyter 环境创建下载链接
    print("\n✨ 请点击以下链接下载您的 Dasha 表格：")
    display(FileLink(output_filename))