# quant_astro/api.py

from .kp import get_kp_lords
from .display import display_kp_table

def calculate_and_display_kp(planet_pos, house_pos):
    """
    一键计算并显示行星和宫位的KP信息。

    这个便捷函数整合了KP计算和HTML表格显示的步骤，
    让用户在获取基础位置后，只需一行代码即可生成所需的核心KP星盘。

    参数:
        planet_pos (dict): `calculate_positions` 函数返回的行星位置字典。
        house_pos (dict): `calculate_positions` 函数返回的宫头位置字典。
    """
    print("🚀 正在执行一键式 KP 分析并生成显示表格...")

    # 1. 将您关心的行星和宫位数据整合到一起
    points_to_analyze = {**planet_pos, **house_pos}

    # 2. 调用核心函数计算所有点的KP星主信息
    #    (这一步在后台完成，您无需关心)
    kp_results = get_kp_lords(points_to_analyze)

    # 3. 将计算结果分离，以便分别传入显示函数
    #    (这一步也在后台完成)
    kp_planets = {k: kp_results[k] for k in planet_pos.keys() if k in kp_results}
    kp_houses = {k: kp_results[k] for k in house_pos.keys() if k in kp_results}

    # 4. 调用显示函数，只生成您需要的两个表格
    display_kp_table("✨ 行星位置 (KP)", kp_planets)
    display_kp_table("🏠 宫头位置 (KP)", kp_houses)
    
    print("✅ KP 表格已成功显示！")