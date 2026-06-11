# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'

# 看OK文件里所有批次都用的是什么店铺全称
seen = set()
for f in sorted(os.listdir(okdir)):
    if not f.endswith('.xlsx') or '\u90e8\u5206' in f: continue
    try:
        df = pd.read_excel(os.path.join(okdir, f), header=1)
        shops = df['\u5e97\u94fa\u540d\u79f0'].unique()
        for s in shops:
            seen.add(s)
    except: pass

print('OK\u6587\u4ef6\u4e2d\u4f7f\u7528\u7684\u5e97\u94fa\u540d\u79f0:')
for s in sorted(seen):
    print(f'  {s}')
