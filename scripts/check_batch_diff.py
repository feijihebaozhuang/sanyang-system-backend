# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'
outdir = r'D:\Desktop\换绑输出'

# 对比第8批：看新8 vs 老8是否相同
old8 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c8\u6279.xlsx'))
new8 = pd.read_excel(os.path.join(outdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c8\u6279.xlsx'))

print(f'OK文件第8批: {len(old8)}条, \u5e97\u94fa={old8["\u5e97\u94fa\u540d\u79f0"].unique()}')
print(f'\u6362\u7ed1\u8f93\u51fa\u7b2c8\u6279: {len(new8)}条, \u5e97\u94fa={new8["\u5e97\u94fa\u540d\u79f0"].unique()}')

# 看换绑输出第1-7批的店铺
for b in range(1,15):
    f = os.path.join(outdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{b}\u6279.xlsx')
    if os.path.exists(f):
        df = pd.read_excel(f)
        shops = df['\u5e97\u94fa\u540d\u79f0'].unique()
        print(f'\u6362\u7ed1\u8f93\u51fa\u7b2c{b}\u6279: {len(df)}条, \u5e97\u94fa={list(shops)}')
