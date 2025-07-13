# quant_astro/display.py

from IPython.display import display, HTML

def _decimal_to_dms_str(decimal_deg):
    """将十进制度数转换为度分秒格式字符串"""
    degrees = int(decimal_deg)
    minutes_full = (decimal_deg - degrees) * 60
    minutes = int(minutes_full)
    seconds = round((minutes_full - minutes) * 60, 2)
    return f"{degrees}°{minutes:02d}'{seconds:05.2f}\""

def display_kp_table(title, kp_results_dict):
    """以HTML表格形式显示KP占星结果"""
    html = f"<h3>{title}</h3><table>"
    html += "<tr><th>对象</th><th>星座</th><th>星座内位置</th><th>恒星</th><th>星座主</th><th>恒星主</th><th>子主</th><th>子子主</th></tr>"

    for name, info in kp_results_dict.items():
        if info is None:
            continue

        sign_degree_dms = _decimal_to_dms_str(info.get('sign_degree', 0))

        html += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td>{info['sign']}</td>
            <td>{sign_degree_dms}</td>
            <td>{info['star']}</td>
            <td>{info['sign_lord']}</td>
            <td>{info['star_lord']}</td>
            <td>{info['sub_lord']}</td>
            <td>{info['sub_sub_lord']}</td>
        </tr>
        """
    html += "</table>"
    display(HTML(html))