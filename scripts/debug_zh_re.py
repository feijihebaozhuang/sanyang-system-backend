# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask = df['店铺简称'].str.contains('止合', na=False)
zh = df[mask].copy().reset_index(drop=True)

# 测哪个匹配不对
for idx in range(len(zh)):
    s = str(zh.iloc[idx]['规格名称']).strip()
    m = re.search(r'【E坑高度(\d+)cm】(.+?)[^；;]*[；;]\d+层[^；;]*[；;]扣底盒【长X宽(\d+)X(\d+)】', s)
    if m:
        h, l, w = m.group(1), m.group(2), m.group(3)
        mat_raw = m.group(2)
        try:
            int(l)
        except:
            print(f'idx={idx}: l={repr(l)}, mat_raw={repr(mat_raw)}')
            print(f'  {s[:80]}')
            break
