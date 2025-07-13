# quant_astro/kp.py

import pandas as pd
import numpy as np
import pkg_resources

def get_kp_lords(positions_dict):
    """
    为一组天体位置查找KP星主信息。

    参数:
        positions_dict: 一个包含天体位置的字典，例如 {'Su': {'lon': 243.28}, ...}
        
    返回:
        一个包含KP星主信息的字典。
    """
    # 使用 pkg_resources 来安全地获取包内数据文件的路径
    csv_path = pkg_resources.resource_filename('quant_astro', 'data/sub-sub.csv')
    
    df = pd.read_csv(csv_path)
    df['To'] = np.where(df['To'] == 0, 360.0, df['To'])
    
    from_arr = df['From'].values.astype('float64')
    to_arr = df['To'].values.astype('float64')
    records = df.to_dict('records')

    results = {}
    for name, data in positions_dict.items():
        lon = float(data['lon'])
        mask = (from_arr <= lon) & (lon < to_arr)
        
        if np.any(mask):
            row = records[np.argmax(mask)]
            results[name] = {
                'sign': row['Sign'],
                'star': row['Star'],
                'sign_lord': row['Sign-Lord'],
                'star_lord': row['Star-Lord'],
                'sub_lord': row['Sub-Lord'],
                'sub_sub_lord': row['Sub-Sub-Lord'],
                'sign_degree': lon % 30
            }
        else:
            results[name] = None
            
    return results