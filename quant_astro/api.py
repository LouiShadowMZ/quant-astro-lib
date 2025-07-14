# quant_astro/api.py

import pandas as pd
from IPython.display import display, FileLink
import os  # <--- 1. 新增导入 os 模块，用于处理文件路径

from .core import calculate_positions
# 假设您已将 dasha_logic.py 重命名为 dasha_Vimshottari.py
from .dasha_Vimshottari import _generate_dasha_periods 

# 2. 更新函数定义，增加 output_dir 参数
def create_dasha_table(
    birth_config, 
    dasa_config, 
    output_filename="dasha_table.csv", 
    output_dir="." # <--- 新增参数，默认值为"."，代表当前目录
):
    """
    Generates a Vimshottari Dasha table and saves it to a specified directory.

    Args:
        birth_config (dict): A dictionary containing birth information.
        dasa_config (dict): A dictionary containing Dasha calculation settings.
        output_filename (str): The name for the output CSV file.
        output_dir (str): The directory where the CSV file will be saved. 
                              Defaults to the current directory.
    """
    try:
        print("Step 1: Calculating planetary positions...")
        planet_positions, _, _, _ = calculate_positions(
            local_time_str=birth_config["local_time_str"],
            timezone_str=birth_config["timezone_str"],
            latitude_str=birth_config["latitude_str"],
            longitude_str=birth_config["longitude_str"],
            elevation=birth_config["elevation"]
        )
        print("Step 2: Generating Dasha periods. This may take a moment...")
        all_intervals = _generate_dasha_periods(planet_positions, birth_config, dasa_config)

        print(f"Step 3: Formatting data for {len(all_intervals)} periods...")
        output_data = []
        for name, start, _ in all_intervals:
            level_planet = name.split()
            level = level_planet[0][1:]
            planet = level_planet[1]
            start_str = start.strftime('%Y-%m-%d %H:%M:%S.%f')
            output_data.append([level, planet, start_str])

        df = pd.DataFrame(output_data, columns=["Level", "Planet", "Date"])

        # --- 3. 核心修改：处理输出路径 ---
        # 如果指定的目录不存在，则创建它
        os.makedirs(output_dir, exist_ok=True)
        
        # 将目录和文件名合并成一个完整的路径
        full_path = os.path.join(output_dir, output_filename)
        
        print(f"Step 4: Saving to '{full_path}' and creating download link...")
        
        # 保存 DataFrame 到指定的完整路径
        df.to_csv(full_path, index=False, encoding='utf-8')

        # 显示指向新路径的下载链接
        display(FileLink(full_path))
        
        print(f"\n✅ Success! The Dasha table has been generated and saved to '{full_path}'.")
        print(f"If the download doesn't start automatically, click the link above.")

    except Exception as e:
        # 增加一个错误捕获，方便调试
        print(f"❌ 生成失败: {e}")