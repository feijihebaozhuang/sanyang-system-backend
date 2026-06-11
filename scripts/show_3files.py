# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

d = r'D:\Desktop\换绑输出'

# 读三个关键文件
f1 = os.path.join(d, '未匹配平台商品.xlsx')
f2 = os.path.join(d, '无匹配_待处理.xlsx')
f3 = os.path.join(d, '无匹配_5f85处理.xlsx')

for fn, label in [(f1,'未匹配平台商品'), (f2,'无匹配_待处理'), (f3,'无匹配_5f85处理')]:
    if os.path.exists(fn):
        df = pd.read_excel(fn)
        print(f'=== {label} ===')
        print(f'  列: {list(df.columns)}')
        print(f'  行数: {len(df)}')
        for _, r in df.head(2).iterrows():
            vals = [str(x)[:50] for x in r.values]
            print(f'    {vals}')
        print()
    else:
        print(f'{label}: 不存在')
