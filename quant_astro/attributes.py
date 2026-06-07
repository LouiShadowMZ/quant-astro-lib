# quant_astro/attributes.py

# 从 core.py 借入这两个函数，这样 __init__.py 不需要改动
from .core import get_sun_rise_and_lord, get_planetary_hour

# --- 常量定义 ---
ZODIAC_NAMES = ['Ari', 'Tau', 'Gem', 'Cnc', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqr', 'Pis']

# 古典占星/KP/吠陀占星 守护星映射 (Traditional Rulership)
# 0=Ari(Ma), 1=Tau(Ve), 2=Gem(Me), 3=Cnc(Mo), 4=Leo(Su), 5=Vir(Me)
# 6=Lib(Ve), 7=Sco(Ma), 8=Sag(Ju), 9=Cap(Sa), 10=Aqr(Sa), 11=Pis(Ju)
SIGN_LORDS_MAP = {
    0: 'Ma', 1: 'Ve', 2: 'Me', 3: 'Mo', 4: 'Su', 5: 'Me',
    6: 'Ve', 7: 'Ma', 8: 'Ju', 9: 'Sa', 10: 'Sa', 11: 'Ju'
}

# --- 辅助工具 (私有) ---
def _get_sign_info(lon_decimal):
    """根据黄经计算星座和度数"""
    idx = int(lon_decimal / 30) % 12
    lon_in_sign = lon_decimal % 30
    return {
        'sign': ZODIAC_NAMES[idx],
        'lon': lon_in_sign,
        'idx': idx # 保留索引方便后续计算主宰星
    }

# --- 主功能函数 ---

def get_attributes(planet_positions, house_positions):
    """
    接收原始的行星和宫位位置字典，返回占星属性字典。
    
    Returns:
        tuple: (planet_signs, house_signs, planet_houses, house_lords)
    """
    
    # 字典 1: 行星的星座归属
    planet_signs = {
        k: _get_sign_info(v['lon']) 
        for k, v in planet_positions.items()
    }

    # 字典 2: 宫位的星座归属
    house_signs = {
        k: _get_sign_info(v['lon']) 
        for k, v in house_positions.items()
    }

    # 字典 4: 每个宫位的主宰星 (根据宫头星座)
    house_lords = {}
    for h_key, h_info in house_signs.items():
        sign_idx = h_info['idx']
        lord = SIGN_LORDS_MAP.get(sign_idx, 'Unknown')
        house_lords[h_key] = lord

    # 字典 3: 行星的宫位归属 (计算行星落在哪个宫)
    # 逻辑：比较行星黄经与宫头黄经
    planet_houses = {}
    
    # 提取宫头列表并排序 (1-12宫)
    # 格式: [(1, 23.5), (2, 54.2), ...]
    cusps = []
    for i in range(1, 13):
        h_name = f"house {i}"
        if h_name in house_positions:
            cusps.append((i, house_positions[h_name]['lon']))
            
    # 如果没有足够的宫位数据，跳过
    if len(cusps) == 12:
        for p_name, p_data in planet_positions.items():
            p_lon = p_data['lon']
            located_house = None
            
            for i in range(12):
                curr_h, curr_lon = cusps[i]
                next_h, next_lon = cusps[(i + 1) % 12] # 循环回到第1宫
                
                # 处理跨越 360/0 度的情况 (例如 12宫头在 350度, 1宫头在 20度)
                if next_lon < curr_lon: 
                    if p_lon >= curr_lon or p_lon < next_lon:
                        located_house = curr_h
                        break
                else:
                    # 正常情况 (例如 1宫头 20度, 2宫头 50度)
                    if curr_lon <= p_lon < next_lon:
                        located_house = curr_h
                        break
            
            planet_houses[p_name] = located_house
            
    return planet_signs, house_signs, planet_houses, house_lords
