# quant_astro/aspects.py

import math
import re

# ----------------- 工具函数 -----------------

def parse_dms_string(dms_str):
    """
    解析DMS字符串，例如 "16°22′50.661″" 或 "06°"
    返回浮点数度数。
    """
    if not dms_str:
        return 0.0
    
    # 移除可能存在的引号变体
    dms_str = dms_str.replace('"', '').replace('”', '').replace('″', '')
    
    # 提取度
    deg_match = re.search(r'(\d+)\s*[°d]', dms_str)
    deg = float(deg_match.group(1)) if deg_match else 0.0
    
    # 提取分
    min_match = re.search(r'[°d]\s*(\d+)\s*[′\']', dms_str)
    minute = float(min_match.group(1)) if min_match else 0.0
    
    # 提取秒 (支持多位小数)
    sec_match = re.search(r'[′\']\s*([\d.]+)', dms_str)
    # 如果没有分只有度的情况，可能没有秒
    if not sec_match:
         # 尝试直接匹配纯数字作为秒（如果格式是 16°22'50）
         pass 
    sec = float(sec_match.group(1)) if sec_match else 0.0
    
    return deg + minute/60.0 + sec/3600.0

def parse_orb_config(config_str):
    """
    解析类似 "Su: 16°...; Mo: 06°" 的字符串为字典
    """
    orbs = {}
    if not config_str:
        return orbs
    
    # 按分号分割
    items = config_str.split(';')
    for item in items:
        if ':' in item:
            key, val = item.split(':')
            key = key.strip()
            val_float = parse_dms_string(val.strip())
            
            # [修改] 极简逻辑：如果是纯数字，就认为是宫位
            if key.isdigit():
                key = f"house {key}" # 例如 "1" -> "house 1"
            
            # 只要不是空的，就存进去 (不再限制只许行星)
            if key:
                orbs[key] = val_float
    return orbs

def parse_aspect_types(type_list):
    """
    解析相位类型列表，例如 ["0°☌", "90°□"]
    返回列表: [{'angle': 0.0, 'symbol': '☌'}, ...]
    """
    aspects = []
    for item in type_list:
        # 提取前面的数字部分作为角度，剩下的作为符号
        match = re.match(r'([\d.]+)\s*[°]?\s*(.*)', item)
        if match:
            angle = float(match.group(1))
            symbol = match.group(2).strip()
            aspects.append({'angle': angle, 'symbol': symbol})
    return aspects

def get_shortest_distance(lon1, lon2):
    """计算两点在圆周上的最短距离 (0-180)"""
    diff = abs(lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff
    return diff

def is_applying(p1_data, p2_data, target_angle):
    """
    判断是入相位(A)还是出相位(S)
    逻辑：计算下一时刻的距离，如果比当前距离更接近 target_angle，则是入相位
    """
    l1, s1 = p1_data['lon'], p1_data.get('speed', 0)
    l2, s2 = p2_data['lon'], p2_data.get('speed', 0)
    
    # 当前距离
    curr_dist = get_shortest_distance(l1, l2)
    
    # 预测极小时间步长后的位置 (例如1小时 = 1/24天)
    dt = 1.0 / 24.0 
    l1_next = (l1 + s1 * dt) % 360
    l2_next = (l2 + s2 * dt) % 360
    
    next_dist = get_shortest_distance(l1_next, l2_next)
    
    # 计算与目标角度的偏差
    curr_err = abs(curr_dist - target_angle)
    next_err = abs(next_dist - target_angle)
    
    if next_err < curr_err:
        return 'A' # Applying
    else:
        return 'S' # Separating

# ----------------- 核心计算逻辑 -----------------

def calculate_aspects(planet_pos, house_pos, aspect_config):
    """
    核心相位计算函数
    :param planet_pos: 过滤后的行星位置字典 (含 Ra/Ke, 三王星等)
    :param house_pos: 宫位位置字典
    :param aspect_config: 配置字典
    :return: 结果字典 {'orb_mode': [], 'whole_sign_mode': [], 'vedic_mode': []}
    """
    
    results = {}
    
    # 提取配置
    modes = aspect_config.get('modes', [])
    orb_settings = parse_orb_config(aspect_config.get('orb_config_str', ''))
    active_houses = aspect_config.get('active_houses', []) # list of ints
    custom_aspects = parse_aspect_types(aspect_config.get('aspect_types', []))
    
    # 准备参与计算的实体列表
    # 注意：输入到这里的 planet_pos 已经是过滤过的了
    # 按照标准顺序排序，方便查看
    # 直接获取 planet_pos 的键列表，因为 core.py 已经排好序了
    sorted_planets = list(planet_pos.keys())
    # ----------------- [修改结束] -----------------
    
    # --- 1. 容许度模式 (Orb Mode) ---
    if 'orb' in modes:
        orb_results = []
        
        # 构建所有参与对象：行星 + 选中的宫位
        bodies = []
        for p in sorted_planets:
            bodies.append({'name': p, 'type': 'planet', 'data': planet_pos[p]})
            
        for h_idx in active_houses:
            h_key = f"house {h_idx}"
            if h_key in house_pos:
                bodies.append({'name': h_key, 'type': 'house', 'data': house_pos[h_key]})
        
        # 双重循环计算
        n = len(bodies)
        for i in range(n):
            for j in range(i + 1, n):
                b1 = bodies[i]
                b2 = bodies[j]
                
                # 宫位对宫位通常不计算相位，除非有特殊需求。此处按通俗逻辑，跳过 House-House
                if b1['type'] == 'house' and b2['type'] == 'house':
                    continue
                
                # [修改] 不再区分行星还是宫位，统一查表
                orb1 = orb_settings.get(b1['name'], 0.0)
                orb2 = orb_settings.get(b2['name'], 0.0)
                
                # 判罚标准：平均值
                limit = (orb1 + orb2) / 2.0
                
                # 计算实际角度差
                dist = get_shortest_distance(b1['data']['lon'], b2['data']['lon'])
                
                # 检查所有自定义相位类型
                for asp in custom_aspects:
                    target = asp['angle']
                    diff = abs(dist - target)
                    
                    if diff <= limit:
                        # 形成相位
                        is_app = is_applying(b1['data'], b2['data'], target)
                        
                        orb_results.append({
                            'p1': b1['name'],
                            'p2': b2['name'],
                            'type': asp['symbol'],
                            'angle_def': target, # 定义的角度
                            'actual_dist': round(dist, 10), # 实际度数
                            'orb': round(diff, 10), # 误差
                            'state': is_app
                        })
        results['orb_mode'] = orb_results

    # --- 2. 整宫制模式 (Whole Sign) ---
    if 'whole_sign' in modes:
        ws_results = []
        
        # 仅行星参与 (含 Ra/Ke/三王星)
        for i in range(len(sorted_planets)):
            for j in range(i + 1, len(sorted_planets)):
                p1 = sorted_planets[i]
                p2 = sorted_planets[j]
                
                lon1 = planet_pos[p1]['lon']
                lon2 = planet_pos[p2]['lon']
                
                # 计算星座索引 (0-11)
                sign1 = int(lon1 / 30)
                sign2 = int(lon2 / 30)
                
                # 距离 (星座格数)
                diff_signs = abs(sign1 - sign2)
                if diff_signs > 6:
                    diff_signs = 12 - diff_signs
                
                symbol = None
                # 托勒密相位映射
                if diff_signs == 0: symbol = '☌' # Conjunction (0)
                elif diff_signs == 1: pass      # Semi-sextile (30) - 非托勒密
                elif diff_signs == 2: symbol = '⚹' # Sextile (60)
                elif diff_signs == 3: symbol = '□' # Square (90)
                elif diff_signs == 4: symbol = '△' # Trine (120)
                elif diff_signs == 5: pass      # Quincunx (150) - 非托勒密
                elif diff_signs == 6: symbol = '☍' # Opposition (180)
                
                if symbol:
                    # 整宫制一般不讲入/出相位，或者也可以算，这里保留入/出计算增强信息
                    # 但实际角度使用 Sign 角度？不，通常直接输出关系即可。
                    # 为了统一格式，我们依然计算 App/Sep 基于实际位置
                    target_map = {0:0, 2:60, 3:90, 4:120, 6:180}
                    target_angle = target_map.get(diff_signs, 0)
                    is_app = is_applying(planet_pos[p1], planet_pos[p2], target_angle)
                    
                    ws_results.append({
                        'p1': p1,
                        'p2': p2,
                        'type': symbol,
                        'state': is_app
                    })
        results['whole_sign_mode'] = ws_results

    # --- 3. 印度模式 (Vedic) ---
    if 'vedic' in modes:
        vedic_results = []
        
        # [逻辑确认] 即使叫整宫/印度，计算基础必须是纯“星座”。
        # 我们使用 int(lon / 30) 确定星座索引 (0=Ari, 1=Tau... 11=Pis)，完全不依赖 House Pos。
        
        # 罗睺计都 (Ra/Ke) 不作为施法者 (Caster)，只作为接收者 (Receiver)
        casters = [p for p in sorted_planets if p not in ['Ra', 'Ke']]
        receivers = sorted_planets 
        
        # [新增] 用于记录已存在的合相 (Yuti) 对，防止 A-B 和 B-A 重复出现
        yuti_pairs = set()

        for caster in casters:
            for receiver in receivers:
                if caster == receiver:
                    continue
                
                # 1. 获取纯黄道经度
                lon1 = planet_pos[caster]['lon']
                lon2 = planet_pos[receiver]['lon']
                
                # 2. 纯星座计算 (0-11)
                s1 = int(lon1 / 30)
                s2 = int(lon2 / 30)
                
                # 3. 计算相对宫位 (印度算法: Inclusive Count)
                # 也就是：从 s1 数到 s2 共有几个星座?
                count = (s2 - s1) % 12 + 1
                
                aspect_symbol = None

                # 规则 0: 合相 (同宫) - [新增去重逻辑]
                if count == 1:
                    # 构建排序元组，确保 (Su, Mo) 和 (Mo, Su) 是同一个 Key
                    pair_key = tuple(sorted((caster, receiver)))
                    
                    if pair_key in yuti_pairs:
                        # 如果这对CP已经记录过，跳过
                        continue
                    else:
                        # 第一次遇到，记录并在下面添加
                        yuti_pairs.add(pair_key)
                        aspect_symbol = '☌'

                # 规则 1: 所有行星对第7宫 (对冲)
                # 注意：对冲在印度占星是视线 (Drishti)，通常视为单向动作，所以一般不强制去重。
                # (如 A 看 B，同时 B 看 A)。保留双向记录是符合惯例的。
                elif count == 7:
                    aspect_symbol = '☍'
                
                # 规则 2: 火星 (4, 8)
                if caster == 'Ma':
                    if count == 4: aspect_symbol = 'Ma-4' 
                    if count == 8: aspect_symbol = 'Ma-8'
                
                # 规则 3: 木星 (5, 9)
                if caster == 'Ju':
                    if count == 5: aspect_symbol = 'Ju-5' 
                    if count == 9: aspect_symbol = 'Ju-9'
                
                # 规则 4: 土星 (3, 10)
                if caster == 'Sa':
                    if count == 3: aspect_symbol = 'Sa-3'
                    if count == 10: aspect_symbol = 'Sa-10'
                
                if aspect_symbol:
                    vedic_results.append({
                        'p1': caster,
                        'p2': receiver,
                        'type': aspect_symbol,
                        'state': 'Exact' 
                    })
                    
        results['vedic_mode'] = vedic_results

    return results