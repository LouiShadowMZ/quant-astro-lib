# quant_astro/api.py

from .core import calculate_positions
from .dasha import generate_dasha_table
from datetime import datetime
import os

def create_dasha_table(birth_config, dasa_config, output_dir="."):
    """
    一键生成 Dasha 表格并保存为 CSV 文件。
    
    参数:
        birth_config (dict): 包含出生信息的字典。
            - "local_time_str": "YYYY-MM-DD HH:MM:SS.ffffff"
            - "timezone_str": "+8:00"
            - "latitude_str": "31N13'57.07\""
            - "longitude_str": "121E28'11.84\""
            - "elevation": (可选)
            
        dasa_config (dict): 包含 Dasha 计算配置的字典。
            - "max_level": 4
            - "output_mode": "all" or "present"
            - "days_in_year": 365.25
            
        output_dir (str): 保存 CSV 文件的目录路径。默认为当前目录。
        
    返回:
        生成的 CSV 文件的完整路径。
    """
    # 1. 调用 core 模块计算行星位置
    planet_positions, _, _, _ = calculate_positions(
        local_time_str=birth_config["local_time_str"],
        timezone_str=birth_config["timezone_str"],
        latitude_str=birth_config["latitude_str"],
        longitude_str=birth_config["longitude_str"],
        elevation=birth_config.get("elevation", 0)
    )
    
    # 2. 提取月亮经度 (lon) 和出生时间
    moon_lon = planet_positions['Mo']['lon']
    birth_dt_obj = datetime.strptime(birth_config["local_time_str"], "%Y-%m-%d %H:%M:%S.%f")
    
    # 3. 调用 dasha 模块生成 Dasha 表格的 DataFrame
    dasha_df = generate_dasha_table(
        moon_lon=moon_lon,
        birth_datetime=birth_dt_obj,
        days_in_year=dasa_config["days_in_year"],
        max_level=dasa_config["max_level"],
        output_mode=dasa_config["output_mode"]
    )
    
    # 4. 保存为 CSV 文件并返回路径
    # 创建一个有意义的文件名
    time_str_for_filename = birth_dt_obj.strftime('%Y%m%d_%H%M%S')
    output_filename = f"dasha_table_{time_str_for_filename}.csv"
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    full_path = os.path.join(output_dir, output_filename)
    dasha_df.to_csv(full_path, index=False)
    
    return full_path