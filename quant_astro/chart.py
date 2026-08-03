# quant_astro/chart.py

import json
import os
from .core import decimal_to_dms

def _decimal_to_zodiac_parts(lon):
    """
    辅助函数：仅用于生成 JSON 数据
    """
    ZODIAC_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
    normalized_lon = lon % 360
    sign_index = int(normalized_lon // 30)
    remainder = normalized_lon - (sign_index * 30)
    deg = int(remainder)
    minutes_float = (remainder - deg) * 60
    minutes = int(minutes_float)
    return {
        'sign_idx': sign_index,
        'sign_sym': ZODIAC_SYMBOLS[sign_index],
        'deg': deg,
        'min': minutes,
        'abs_lon': lon
    }

def generate_chart_html(planet_pos, house_pos, 
                        # 新增参数接收你的字典数据
                        chart_info=None,        # 接收 chart_name, birth_config, options 的合并字典
                        kp_planet_results=None, # 接收 kp_planet_results
                        kp_house_results=None,  # 接收 kp_house_results
                        kp_planet_sigs=None,    # 接收 kp_planet_sigs
                        kp_house_sigs=None,     # 接收 kp_house_sigs
                        kp_ruling_planets=None, # 接收 kp_ruling_planets

                        # === 新增参数 ===
                        aspect_results=None,     # 接收 aspects.py 的计算结果
                        aspect_config=None,      # 接收相位配置 (含 active_houses)
                        calculation_options=None,# 接收计算配置 (含 selected_planets)


                        output_filename=None):
    """
    生成 HTML，纯 UI 渲染。
    已更新：支持详细的 KP 各种表格数据传入
    """
    
     # ================= [【修改2】动态提取文件名开始] =================
    if not output_filename:
        filename_str = None
        if isinstance(chart_info, dict):
            # 情况 A: chart_info 是合并字典，里面有 'chart_name' 字典
            if 'chart_name' in chart_info and isinstance(chart_info['chart_name'], dict):
                filename_str = chart_info['chart_name'].get('matter_name')
            # 情况 B: chart_info 直接就是 chart_name 字典 (如 {'matter_name': '28 证券操纵官非'})
            elif 'matter_name' in chart_info:
                filename_str = chart_info.get('matter_name')
            # 情况 C: chart_info['chart_name'] 直接是字符串
            elif 'chart_name' in chart_info and isinstance(chart_info['chart_name'], str):
                filename_str = chart_info['chart_name']

        if filename_str:
            filename_str = str(filename_str).strip()
            output_filename = filename_str if filename_str.lower().endswith('.html') else f"{filename_str}.html"
        else:
            output_filename = "astro_chart_final.html" # 兜底默认文件名
    # ================= [动态提取文件名结束] =================

    # 1. 转换数据为前端格式
    chart_dict = {
        'asc_lon': house_pos['house 1']['lon'],
        'houses': [],
        'planets': [],
        # 预留给前端的数据容器
        'kp_data': {'planets': [], 'houses': []},
        'kp_sigs': {'planets': kp_planet_sigs, 'houses': kp_house_sigs},
        'kp_ruling': kp_ruling_planets,
        'chart_info': chart_info 
    }

    # ================= [相位插入开始] =================
    # 初始化新增的容器
    chart_dict['aspects'] = {}
    chart_dict['settings'] = {}

    # 1. 注入配置信息 (前端 JS 生成骨架需要用到 selected_planets 和 active_houses)
    # 只有当传入了 calculation_options 且里面有 selected_planets 时才注入
    if calculation_options and 'selected_planets' in calculation_options:
        chart_dict['settings']['selected_planets'] = calculation_options['selected_planets']
    
    # 只有当传入了 aspect_config 且里面有 active_houses 时才注入
    if aspect_config and 'active_houses' in aspect_config:
        chart_dict['settings']['active_houses'] = aspect_config['active_houses']

    # 2. 注入相位结果 (按需注入，如果某个模式没算出来，就不传给前端，防止前端报错)
    if aspect_results:
        # 检查容许度模式
        if 'orb_mode' in aspect_results and aspect_results['orb_mode']:
            chart_dict['aspects']['orb'] = aspect_results['orb_mode']
        
        # 检查整宫制模式
        if 'whole_sign_mode' in aspect_results and aspect_results['whole_sign_mode']:
            chart_dict['aspects']['whole_sign'] = aspect_results['whole_sign_mode']
            
        # 检查印度模式
        if 'vedic_mode' in aspect_results and aspect_results['vedic_mode']:
            chart_dict['aspects']['vedic'] = aspect_results['vedic_mode']
    # ================= [相位插入结束] =================

    # (1) 处理宫位 (保持原有逻辑)
    sorted_keys = sorted(house_pos.keys(), key=lambda x: int(x.replace('house ', '')))
    house_list_temp = []

    for key in sorted_keys:
        val = house_pos[key]
        h_id = int(key.replace('house ', ''))
        house_obj = {
            'id': h_id,
            'abs_lon': val['lon'],
            'zodiac': _decimal_to_zodiac_parts(val['lon'])
        }
        chart_dict['houses'].append(house_obj)
        house_list_temp.append(house_obj)

    # (2) 处理宫位中点 (保持原有逻辑)
    midpoints = []
    for i in range(12):
        curr = house_list_temp[i]['abs_lon']
        next_h = house_list_temp[(i + 1) % 12]['abs_lon']
        diff = (next_h - curr) % 360
        mid_lon = (curr + diff / 2) % 360
        midpoints.append({'id': house_list_temp[i]['id'], 'lon': mid_lon})
    chart_dict['house_mids'] = midpoints

    # (3) 处理行星 (保持原有逻辑)
    for p_key, p_val in planet_pos.items():
        chart_dict['planets'].append({
            'name': p_key,
            'is_retro': p_val.get('speed', 0) < 0,
            'zodiac': _decimal_to_zodiac_parts(p_val['lon']),
            'abs_lon': p_val['lon']
        })

    # (4) 处理 KP 基础表格数据 (整合你的两个新字典 kp_planet_results 和 kp_house_results)
    # 辅助函数：处理单行数据
    def _process_kp_row(name, data, target_list, sort_key=None):
        if not data: return
        dms_info = decimal_to_dms(data['sign_degree'])
        row_data = {
            'name': name,
            'sign': data['sign'],
            'pos_str': dms_info['str'],
            'star': data['star'],
            'rl': data['sign_lord'],
            'nl': data['star_lord'],
            'sl': data['sub_lord'],
            'ssl': data['sub_sub_lord'],
            'paada': data.get('paada', '-')
        }
        if sort_key: row_data['sort_id'] = sort_key
        target_list.append(row_data)

    # 处理行星 KP
    if kp_planet_results:
        for name, data in kp_planet_results.items():
            _process_kp_row(name, data, chart_dict['kp_data']['planets'])
            
    # 处理宫位 KP
    if kp_house_results:
        for name, data in kp_house_results.items():
            h_num = int(name.replace('house ', ''))
            _process_kp_row(str(h_num), data, chart_dict['kp_data']['houses'], sort_key=h_num)
        # 排序宫位
        chart_dict['kp_data']['houses'].sort(key=lambda x: x['sort_id'])

    json_output = json.dumps(chart_dict, indent=2)

    # 3. 定义资源绝对路径
    base_path = "file:///D:/github/my_astro_project/html"

    # 4. 生成 HTML 内容
    html_content = f"""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>Astrology Chart</title>
    <!-- 引用绝对路径的 CSS -->
    <link rel="stylesheet" href="{base_path}/astro_style.css">
    <!-- 引用绝对路径的 JS (配置 + 渲染逻辑) -->
    <script src="{base_path}/astro_style_config.js"></script>
</head>
<body>

    <div id="svgChartContainer" class="chart-container"></div>

    <div id="southIndianChart" class="south-indian-chart"></div>

     <!-- [新增] 相位表大容器 -->
    <div id="aspectsContainer" class="aspects-main-container"></div>

    <div id="tableContainer" class="astro-table-container">
        
        <div class="table-block" id="block-info">
        <h3 style="color:#e6edf3; text-align:center; border-bottom: 2px solid #30363d; padding-bottom: 10px;">📋 占星配置信息</h3>
        <div id="infoTable"></div>
        </div>

        <div class="table-block" id="block-ruling">
        <h3 style="color:#e6edf3; text-align:center; margin-top:30px;">👑 主宰星</h3>
        <div id="rulingTable"></div>
        </div>

        <div class="table-block" id="block-kp-planet">
        <h3 style="color:#e6edf3; text-align:center; margin-top:30px;">✨ 行星 KP</h3>
        <div id="kpPlanetTable"></div>
        </div>

        <div class="table-block" id="block-kp-house">
        <h3 style="color:#e6edf3; text-align:center; margin-top:30px;">🏠 宫位 KP</h3>
        <div id="kpHouseTable"></div>
        </div>

        <div class="table-block" id="block-sig-planet">
        <h3 style="color:#e6edf3; text-align:center; margin-top:30px;">🌟 行星象征宫位</h3>
        <div id="sigPlanetTable"></div>
        </div>

        <div class="table-block" id="block-sig-house">
        <h3 style="color:#e6edf3; text-align:center; margin-top:30px;">🏰 宫位象征星</h3>
        <div id="sigHouseTable"></div>
        </div>

    </div>

<script>
// 1. 注入数据 (来自 Python)
const CHART_DATA = {json_output};


// 2. 启动渲染
// 确保 external JS 加载完成后执行
window.onload = function() {{
    // 渲染星盘
    if (window.renderAstroChart) {{
        window.renderAstroChart(CHART_DATA);
    }} else {{
        console.error("renderAstroChart 未定义，请检查 astro_style_config.js 是否加载成功");
    }}

    // [新增] 渲染南印度方盘
    if (window.renderSouthIndianChart) {{
        window.renderSouthIndianChart(CHART_DATA);
    }}

    // [新增] 渲染相位表 (这一段是新加的)
    if (window.renderAspectTables) {{
        window.renderAspectTables(CHART_DATA);
    }}

    // 渲染 KP 表格
    if (window.renderKpTables) {{
        window.renderKpTables(CHART_DATA);
    }}
}};

</script>
</body>
</html>
"""

    # 写入文件
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ HTML生成完毕: {output_filename}")
    print(f"🔗 关联配置: {base_path}/astro_style_config.js")