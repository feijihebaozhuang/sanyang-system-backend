# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'
outdir = r'D:\Desktop\换绑输出'

# 看OK文件已通过的格式
f_ok = os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c32\u6279.xlsx')
df_ok = pd.read_excel(f_ok)
print(f'OK\u6587\u4ef6\u7b2c32\u6279:')
print(f'  \u5217\u540d: {list(df_ok.columns)}')
print(f'  \u884c\u6570: {len(df_ok)}')
for _, r in df_ok.head(3).iterrows():
    print(f'  {[str(x)[:30] for x in r.values]}')

print()

# 看新生成的第8批
f_new = os.path.join(outdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c8\u6279.xlsx')
df_new = pd.read_excel(f_new)
print(f'\u6362\u8f93\u7b2c8\u6279:')
print(f'  \u5217\u540d: {list(df_new.columns)}')
print(f'  \u884c\u6570: {len(df_new)}')
for _, r in df_new.head(3).iterrows():
    print(f'  {[str(x)[:30] for x in r.values]}')

print()
print('OK\u6587\u4ef6\u5df2\u6709: 1-32\u6279')
print('\u6362\u8f93\u65b0\u751f\u6210: 1-14\u6279')
print('\u5176\u4e2d\u7b2c1-7\u6279\u548cOK\u6587\u4ef6\u91cd\u590d\uff0c\u53ea\u9700\u5c06\u7b2c8-14\u6279\u52a0\u5165OK\u6587\u4ef6')
print('\u5bf9\u5e94\u5173\u7cfb: 8->33, 9->34, 10->35, 11->36, 12->37, 13->38, 14->39')
