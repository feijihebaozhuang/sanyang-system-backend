# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

pids = ['5145118190894', '5145118190893', '4863776885263', '4772764692890', '4768923641932']

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
df = pd.read_excel(source, skiprows=2, dtype=str)

for pid in pids:
    mask = df.iloc[:, 8].astype(str).str.strip() == pid
    if mask.any():
        row = df[mask].iloc[0]
        spec = str(row.iloc[5] or '').strip()
        shop = str(row.iloc[1] or '').strip()
        print(f'pid={pid}, shop={shop}, spec={spec[:100]}')
    else:
        # 再尝试列3（平台商品id）
        mask2 = df.iloc[:, 2].astype(str).str.strip() == pid
        if mask2.any():
            row = df[mask2].iloc[0]
            spec = str(row.iloc[5] or '').strip()
            shop = str(row.iloc[1] or '').strip()
            pid8 = str(row.iloc[8] or '').strip()
            print(f'pid={pid} (匹配到列2), pid(列8)={pid8}, shop={shop}, spec={spec[:100]}')
        else:
            print(f'pid={pid} 未在Excel中找到')
