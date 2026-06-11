# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('大鱼', na=False)
df2 = df[mask]

# 第三类: 长Xcm【100个】；宽-高【Y*Zcm】外径
print('=== 第三类：长Xcm【100个】；宽-高【Y*Zcm】外径 ===\n')
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '宽-高' in s:
        m = re.search(r'长(\d+)cm【100个】.*?宽-高【(\d+)\*(\d+)cm】.*?外径', s)
        if m:
            l, w, h = int(m.group(1)), int(m.group(2)), int(m.group(3))
            print('  长=%s 宽=%s 高=%s | 商品ID=%s | 规格ID=%s' % (l, w, h, row['平台商品id'], row['平台规格id']))
            print('    原文: %s' % s)
