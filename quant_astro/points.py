# quant_astro/points.py

import swisseph as swe

def calculate_special_points(ascmc_tuple, custom_points_dict):
    """
    计算专业点和用户自定义点的位置。
    
    参数:
        ascmc_tuple: 从 core.calculate_positions 返回的 ascmc 元组。
        custom_points_dict: 用户定义的点，格式为 {'点名称': 黄经度数}
        
    返回:
        一个元组，包含 (professional_points, custom_points)
    """
    
    # 1. 专业点计算
    professional_points = {}
    ascmc_points_map = {3: 'Vertex', 4: 'Eq. Asc', 7: 'Pol. Asc'}
    
    for index, name in ascmc_points_map.items():
        if index < len(ascmc_tuple):
            lon = ascmc_tuple[index]
            pos_ecl = (lon, 0.0, 1.0)
            pos_eq = swe.cotrans(pos_ecl, swe.FLG_EQUATORIAL)
            professional_points[name] = {'lon': lon % 360, 'lat': 0.0, 'ra': pos_eq[0], 'dec': pos_eq[1]}

    # 2. 自定义点计算
    custom_points = {}
    for name, lon in custom_points_dict.items():
        pos_ecl = (lon, 0.0, 1.0)
        pos_eq = swe.cotrans(pos_ecl, swe.FLG_EQUATORIAL)
        custom_points[name] = {'lon': lon % 360, 'lat': 0.0, 'ra': pos_eq[0], 'dec': pos_eq[1]}
        
    return professional_points, custom_points