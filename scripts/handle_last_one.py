# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
files = os.listdir(OUT_DIR)
pingka_file = [f for f in files if f.startswith('\u5e73') and f.endswith('.xlsx')][0]
PINGKA = os.path.join(OUT_DIR, pingka_file)

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()

# 最后1条手动处理
row = target.iloc[0]
spec = str(row['规格名称'])
pid = str(row['平台商品id'])
spec_id = str(row['平台规格id'])

# C3: 】0.5*16.5*11cm -> 取 ]后面的值
m = re.search(r'】(0\.5)\*([\d.]+)\*([\d.]+)', spec)
if m:
    l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
    print(f'手动解析: C3 L={l} W={w} H={h}')
    
    # 保存到无匹配（这个数据疑似有误，放无匹配更合适）
    nm_path = os.path.join(OUT_DIR, '\u65e0\u5339\u914d_5f85\u5904\u7406.xlsx')
    row_data = ['友尚包装', pid, spec, spec_id, '疑似数据错误可忽略', f'{l}*{w}*{h}-外径-特硬']
    
    if os.path.exists(nm_path):
        df_nm = pd.read_excel(nm_path)
        pd.concat([df_nm, pd.DataFrame([row_data], columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析'])], ignore_index=True).to_excel(nm_path, index=False)
    else:
        pd.DataFrame([row_data], columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析']).to_excel(nm_path, index=False)
    
    # 从平卡删除
    mask_keep = ~df['平台规格id'].astype(str).isin([spec_id])
    df[mask_keep].to_excel(PINGKA, index=False)
    print(f'✅ 已移除最后1条，平卡已清空友尚')
else:
    print('无法解析')
