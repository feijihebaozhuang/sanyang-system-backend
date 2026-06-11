# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('亚润', na=False)
df2 = df[mask]

# 找长度11cm 宽*高【23*11】黄色
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    m = re.search(r'长度\s*11\s*cm;宽\*高【23\*11】.*?黄色', s)
    if m:
        print('原文: %s' % s)
        print('商品ID: %s' % row['平台商品id'])
        print('规格ID: %s' % row['平台规格id'])
        break
