import datetime

# --- 这里定义占位变量，作为接收 Colab 前端包裹的“收件箱” ---
birth_config = {}
calculation_options = {}
sunrise_config = {}
aspect_config = {}
magic_rules = {}
search_config = {}
lunar_phase_orb = 15.0

# ==============================================================================
# ⚙️ 【底层检测引擎】(原封不动粘贴区)
# ==============================================================================

# 👇👇👇👇👇 请把你 Colab 里的代码粘贴在这里 👇👇👇👇👇
# （从 def check_aspect_match 开始，一直粘贴到 def run_magic_election() 整个函数写完为止）
# （注意：最最底下那单独的一句启动命令 run_magic_election() 不要粘进来哦！）



# ==============================================================================
# ⚙️ 【底层检测引擎】 (修复Bug后的坚如磐石版)
# ==============================================================================

# 基础校验组件（适配极简列表结构）
def check_aspect_match(rule, aspect_list):
    """提取极简相位参数并进行双向核对"""
    p1 = rule[0]
    p2 = rule[1]
    allowed_types = rule[2] if len(rule) > 2 else None
    req_state = rule[3] if len(rule) > 3 else None

    # 【修复Bug 2】: 防止用户直接填字符串而不是列表，导致字符串被拆解
    if isinstance(allowed_types, str):
        allowed_types = [allowed_types]

    for asp in aspect_list:
        if (asp['p1'] == p1 and asp['p2'] == p2) or (asp['p1'] == p2 and asp['p2'] == p1):
            if allowed_types and not any(asp['type'] in t for t in allowed_types):
                continue
            if req_state and asp['state'] != req_state:
                continue
            return asp
    return None

def check_sign_rule(rule, p_signs, h_signs):
    entity, allowed_signs = rule[0], rule[1]
    data = p_signs.get(entity) or h_signs.get(entity)
    if not data: return False # 【修复Bug 1】: 找不到数据意味着条件不成立，必须返回 False
    return data["sign"] in allowed_signs

def check_house_rule(rule, p_houses):
    entity, allowed_houses = rule[0], rule[1]
    if entity not in p_houses: return False # 【修复Bug 1】
    return p_houses[entity] in allowed_houses

def check_lon_rule(rule, pos_dict):
    entity, deg_range = rule[0], rule[1]
    if entity not in pos_dict: return False # 【修复Bug 1】
    lon = pos_dict[entity]["lon"]
    return deg_range[0] <= lon <= deg_range[1]

# --- 全新大一统核心处理器 ---

def process_aspects_logic(logic_config, orb_aspects):
    """相位专属漏斗：执行筛选并收集通关护符"""
    valid_aspects = []
    pos_cfg = logic_config.get("POS", {})
    neg_cfg = logic_config.get("NEG", {})

    for group in pos_cfg.get("AND", []):
        if not group: continue # 防爆盾
        for rule in group:
            matched = check_aspect_match(rule, orb_aspects)
            if not matched: return False, []
            valid_aspects.append(matched)

    for group in pos_cfg.get("OR", []):
        if not group: continue # 防爆盾
        group_matched = False
        for rule in group:
            matched = check_aspect_match(rule, orb_aspects)
            if matched:
                group_matched = True
                valid_aspects.append(matched)
                break
        if not group_matched: return False, []

    for group in neg_cfg.get("OR", []):
        if not group: continue
        if any(check_aspect_match(rule, orb_aspects) for rule in group): return False, []

    for group in neg_cfg.get("AND", []):
        if not group: continue
        if all(check_aspect_match(rule, orb_aspects) for rule in group): return False, []

    return True, valid_aspects

def process_standard_logic(logic_config, checker_func, *args):
    """星座、宫位、度数通用漏斗"""
    pos_cfg = logic_config.get("POS", {})
    neg_cfg = logic_config.get("NEG", {})

    for group in pos_cfg.get("AND", []):
        if not group: continue # 防爆盾
        for rule in group:
            if not checker_func(rule, *args): return False

    for group in pos_cfg.get("OR", []):
        if not group: continue # 防爆盾
        if not any(checker_func(rule, *args) for rule in group): return False

    for group in neg_cfg.get("OR", []):
        if not group: continue
        if any(checker_func(rule, *args) for rule in group): return False

    for group in neg_cfg.get("AND", []):
        if not group: continue
        if all(checker_func(rule, *args) for rule in group): return False

    return True

# ... (后面的 evaluate_astrology_conditions 保持你原来的样子即可) ...


def evaluate_astrology_conditions(dt):
    """核心判别器：执行终极统一漏斗"""
    current_birth_config = birth_config.copy()
    current_birth_config['local_time_str'] = dt.strftime("%Y-%m-%d %H:%M:%S.000000")

    planet_pos, house_pos, ascmc_tuple, jd, dignities = qa.calculate_positions(**current_birth_config, **calculation_options)
    planet_signs, house_signs, planet_houses, house_lords = qa.get_attributes(planet_pos, house_pos)
    sunrise_results = qa.get_sun_rise_and_lord(current_birth_config, sunrise_config)
    planetary_hour_data = qa.get_planetary_hour(current_birth_config, sunrise_config)
    aspect_results = qa.calculate_aspects(planet_pos, house_pos, aspect_config)

    orb_aspects = aspect_results.get('orb_mode', [])

    # --- 0. 月相环境校验 ---
    allowed_phases = magic_rules.get("allowed_lunar_phases", [])
    if allowed_phases:
        sun_lon = planet_pos['Su']['lon']
        moon_lon = planet_pos['Mo']['lon']
        phase_angle = (moon_lon - sun_lon) % 360

        if phase_angle <= lunar_phase_orb or phase_angle >= (360 - lunar_phase_orb):
            current_phase = "New"
        elif (180 - lunar_phase_orb) <= phase_angle <= (180 + lunar_phase_orb):
            current_phase = "Full"
        elif phase_angle < 180:
            current_phase = "Waxing"
        else:
            current_phase = "Waning"

        if current_phase not in allowed_phases: return False, None

    # --- 1. 主宰星校验 ---
    if magic_rules["allowed_day_lords"] and sunrise_results['day_lord'] not in magic_rules["allowed_day_lords"]: return False, None
    if magic_rules["allowed_hour_lords"] and planetary_hour_data['planetary_hour_lord'] not in magic_rules["allowed_hour_lords"]: return False, None

    # =========================================================================
    # 终极漏斗开启：贯通 2-6 项所有星象指标
    # =========================================================================

    passed_aspects, valid_aspects_info = process_aspects_logic(magic_rules.get("2_aspects_logic", {}), orb_aspects)
    if not passed_aspects: return False, None

    if not process_standard_logic(magic_rules.get("3_signs_logic", {}), check_sign_rule, planet_signs, house_signs): return False, None
    if not process_standard_logic(magic_rules.get("4_houses_logic", {}), check_house_rule, planet_houses): return False, None
    if not process_standard_logic(magic_rules.get("5_planet_longitude_logic", {}), check_lon_rule, planet_pos): return False, None
    if not process_standard_logic(magic_rules.get("6_house_longitude_logic", {}), check_lon_rule, house_pos): return False, None

    return True, valid_aspects_info

# (原有的 find_exact_boundary 和 run_magic_election 逻辑保持不变即可)

def find_exact_boundary(dt_false, dt_true, is_finding_start):
    left = dt_false if is_finding_start else dt_true
    right = dt_true if is_finding_start else dt_false

    while (right - left).total_seconds() > 1:
        mid_time = left + (right - left) / 2
        mid_time = mid_time.replace(microsecond=0)
        is_valid, _ = evaluate_astrology_conditions(mid_time)

        if is_finding_start:
            if is_valid: right = mid_time
            else: left = mid_time
        else:
            if is_valid: left = mid_time
            else: right = mid_time

    return right if is_finding_start else left

def run_magic_election():
    start_dt = datetime.datetime.strptime(search_config['start_time'], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(search_config['end_time'], "%Y-%m-%d %H:%M:%S")
    step = datetime.timedelta(minutes=search_config['coarse_step_minutes'])

    print(f"🌟 启动行星魔法择时引擎 (全域无限积木终极版)...")
    print(f"⏳ 巡航区间: {start_dt} 至 {end_dt}")
    print("-" * 50)

    windows = []
    current_dt = start_dt
    in_window = False
    window_start_exact = None

    while current_dt <= end_dt:
        is_valid, _ = evaluate_astrology_conditions(current_dt)

        if is_valid and not in_window:
            in_window = True
            window_start_exact = start_dt if current_dt == start_dt else find_exact_boundary(current_dt - step, current_dt, True)

        elif not is_valid and in_window:
            in_window = False
            exact_end = find_exact_boundary(current_dt - step, current_dt, False)

            _, exact_aspects = evaluate_astrology_conditions(window_start_exact)
            aspect_str = ""
            if exact_aspects:
                texts = [f"{asp['p1']}{asp['type']}{asp['p2']}({'入相' if asp['state']=='A' else '出相' if asp['state']=='S' else '精准'}, 容差{asp['orb']:.1f}°)" for asp in exact_aspects]
                aspect_str = " | 触发条件: " + ", ".join(texts)

            windows.append((window_start_exact, exact_end))
            print(f"✨ 捕获护符窗口: {window_start_exact} 至 {exact_end} (持续: {exact_end - window_start_exact}){aspect_str}")

        current_dt += step

    if in_window:
        _, exact_aspects = evaluate_astrology_conditions(window_start_exact)
        aspect_str = ""
        if exact_aspects:
            texts = [f"{asp['p1']}{asp['type']}{asp['p2']}" for asp in exact_aspects]
            aspect_str = " | 触发: " + ", ".join(texts)
        windows.append((window_start_exact, end_dt))
        print(f"✨ 捕获护符窗口(截断): {window_start_exact} 至 {end_dt} (持续: {end_dt - window_start_exact}){aspect_str}")

    print("-" * 50)
    print(f"🎯 择时计算完成！共找到 {len(windows)} 个完美时刻段。")




# 👆👆👆👆👆 粘贴结束 👆👆👆👆👆

# ==============================================================================
# 🚀 接收前端指令的“终极触发器” (不要修改这里)
# ==============================================================================
def start_magic_engine(configs):
    """
    这正是跨云端呼叫的核心魔法：
    把你 Colab 里传过来的配置字典，全部拆解并装入我们头部的“收件箱”中。
    这样你原本的代码一抬头，就能像以前一样无缝看到所有配置！
    """
    global birth_config, calculation_options, sunrise_config, aspect_config, magic_rules, search_config, lunar_phase_orb
    
    birth_config = configs.get('birth_config', {})
    calculation_options = configs.get('calculation_options', {})
    sunrise_config = configs.get('sunrise_config', {})
    aspect_config = configs.get('aspect_config', {})
    magic_rules = configs.get('magic_rules', {})
    search_config = configs.get('search_config', {})
    lunar_phase_orb = configs.get('lunar_phase_orb', 15.0)

    # 动态召唤你自己的核心占星库 (放在这里导入，能完美避开 GitHub 初始化库时的循环引用冲突)
    global qa
    import quant_astro as qa

    # 按下你原本的启动按钮！
    run_magic_election()