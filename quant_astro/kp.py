# quant_astro/kp.py

import pandas as pd
import numpy as np
import pkg_resources

def get_kp_lords(planet_dict, house_dict):
    """
    为行星和宫位分别查找KP星主信息。
    
    参数:
        planet_dict: 行星位置字典
        house_dict: 宫位位置字典
        
    返回:
        (planet_results, house_results): 两个独立的字典
    """
    # 使用 pkg_resources 来安全地获取包内数据文件的路径
    csv_path = pkg_resources.resource_filename('quant_astro', 'data/sub-sub.csv')
    
    df = pd.read_csv(csv_path)
    df['To'] = np.where(df['To'] == 0, 360.0, df['To'])
    
    from_arr = df['From'].values.astype('float64')
    to_arr = df['To'].values.astype('float64')
    records = df.to_dict('records')

    # 定义一个内部函数来处理单个字典，避免代码重复
    def process_single_dict(input_dict):
        output_results = {}
        for name, data in input_dict.items():
            lon = float(data['lon'])
            mask = (from_arr <= lon) & (lon < to_arr)
            
            if np.any(mask):
                row = records[np.argmax(mask)]
                output_results[name] = {
                    'sign': row['Sign'],
                    'star': row['Star'],
                    'sign_lord': row['Sign-Lord'],
                    'star_lord': row['Star-Lord'],
                    'sub_lord': row['Sub-Lord'],
                    'sub_sub_lord': row['Sub-Sub-Lord'],
                    'sign_degree': lon % 30,
                    'paada': row['paada']
                }
            else:
                output_results[name] = None
        return output_results

    # 分别处理两个字典
    planet_results = process_single_dict(planet_dict)
    house_results = process_single_dict(house_dict)
            
    return planet_results, house_results


def get_significators(planet_pos, house_pos, kp_planet_results, kp_house_results):
    """
    计算KP占星中的行星象征星(Planet Significators)和宫位象征星(House Significators)。
    完全基于遍历逻辑复刻。
    """
    
    # === 1. 准备工作：建立映射表 ===
    
    # 1.1 整理宫头经度
    house_longitudes = {}
    for key, data in house_pos.items():
        if 'house' in key:
            h_num = int(key.replace('house', '').strip())
            house_longitudes[h_num] = float(data['lon'])
    
    # 1.2 建立 [Occupants Map]: 谁落在哪个宫？
    planet_occupancy = {} 
    
    # 辅助：计算落宫
    def get_house_of_lon(lon, houses_lon):
        for i in range(1, 13):
            cusp_curr = houses_lon[i]
            next_idx = i + 1 if i < 12 else 1
            cusp_next = houses_lon[next_idx]
            
            if cusp_curr < cusp_next:
                if cusp_curr <= lon < cusp_next:
                    return i
            else: # 跨越0度
                if cusp_curr <= lon < 360 or 0 <= lon < cusp_next:
                    return i
        return None

    for p_name, p_data in planet_pos.items():
        h_num = get_house_of_lon(float(p_data['lon']), house_longitudes)
        if h_num:
            planet_occupancy[p_name] = h_num

    # 1.3 建立 [Ownership Map]: 谁守护哪个宫？
    planet_ownership = {p: [] for p in planet_pos.keys()}
    
    for h_key, h_data in kp_house_results.items():
        if h_data:
            lord = h_data['sign_lord']
            h_num = int(h_key.replace('house', '').strip())
            if lord in planet_ownership:
                planet_ownership[lord].append(h_num)

    # 1.4 建立 [Starlord Map]: 谁是谁的宿主？
    planet_starlord_map = {}
    for p_name, p_data in kp_planet_results.items():
        if p_data:
            planet_starlord_map[p_name] = p_data['star_lord']

    # === 2. 计算 Planet Significators (ABCD) ===
    planet_sigs = {}
    
    for p in planet_pos.keys():
        star_lord = planet_starlord_map.get(p)
        
        # Level B: 行星落宫
        level_b = [planet_occupancy.get(p)] if p in planet_occupancy else []
        # Level D: 行星守护宫
        level_d = planet_ownership.get(p, [])
        # Level A: 宿主落宫
        level_a = []
        if star_lord and star_lord in planet_occupancy:
            level_a = [planet_occupancy[star_lord]]
        # Level C: 宿主守护宫
        level_c = []
        if star_lord:
            level_c = planet_ownership.get(star_lord, [])
            
        planet_sigs[p] = {
            'A': sorted(list(set(level_a))),
            'B': sorted(list(set(level_b))),
            'C': sorted(list(set(level_c))),
            'D': sorted(list(set(level_d)))
        }

    # === 3. 计算 House Significators (1234) ===
    house_sigs = {}
    
    # 辅助：反转map获取宫内星
    house_occupants = {i: [] for i in range(1, 13)}
    for p, h in planet_occupancy.items():
        house_occupants[h].append(p)

    for h_num in range(1, 13):
        h_key = f"house {h_num}"
        h_data = kp_house_results.get(h_key)
        
        if not h_data: continue
            
        # Level 4: 宫主星
        lord = h_data['sign_lord']
        level_4 = [lord] if lord in planet_pos else []
        
        # Level 2: 宫内星
        level_2 = house_occupants[h_num]
        
        # Level 3: 宿主是宫主星(Level 4)的行星
        level_3 = []
        for p, s_lord in planet_starlord_map.items():
            if s_lord == lord:
                level_3.append(p)
                
        # Level 1: 宿主是宫内星(Level 2)的行星
        level_1 = []
        for occupant in level_2:
            for p, s_lord in planet_starlord_map.items():
                if s_lord == occupant:
                    level_1.append(p)
        
        house_sigs[h_num] = {
            '1': sorted(list(set(level_1))),
            '2': sorted(list(set(level_2))),
            '3': sorted(list(set(level_3))),
            '4': sorted(list(set(level_4)))
        }

    return planet_sigs, house_sigs

def get_ruling_planets(kp_planet_results, kp_house_results, day_lord):
    """
    提取KP系统中的主宰星（Ruling Planets）。
    包含：Asc的宫/宿/Sub，Moon的宫/宿/Sub，以及值日星。
    """
    # 获取第1宫（上升）的数据，如果没找到则为空字典
    asc_data = kp_house_results.get('house 1', {})
    # 获取月亮的数据
    moon_data = kp_planet_results.get('Mo', {})

    ruling_planets = {
        'Asc_Sign_Lord': asc_data.get('sign_lord'),
        'Asc_Star_Lord': asc_data.get('star_lord'),
        'Asc_Sub_Lord':  asc_data.get('sub_lord'),
        'Moon_Sign_Lord': moon_data.get('sign_lord'),
        'Moon_Star_Lord': moon_data.get('star_lord'),
        'Moon_Sub_Lord':  moon_data.get('sub_lord'),
        'Day_Lord':       day_lord
    }

    return ruling_planets