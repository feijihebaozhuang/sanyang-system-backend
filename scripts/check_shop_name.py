# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'

# 看OK文件已通过的店铺名称
f32 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c32\u6279.xlsx'), header=1)
print(f'OK\u6587\u4ef6\u7b2c32\u6279 - \u5e97\u94fa: {f32["\u5e97\u94fa\u540d\u79f0"].unique()}')

# 看新第33批
f33 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c33\u6279.xlsx'), header=1)
print(f'\u65b0\u7b2c33\u6279 - \u5e97\u94fa: {f33["\u5e97\u94fa\u540d\u79f0"].unique()}')

# 看新第34批
f34 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c34\u6279.xlsx'), header=1)
print(f'\u65b0\u7b2c34\u6279 - \u5e97\u94fa: {f34["\u5e97\u94fa\u540d\u79f0"].unique()}')

# 看OK文件其他批次的店铺名称，找出完整名称
f1 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c1\u6279.xlsx'), header=1)
print(f'\u65e7\u7b2c1\u6279 - \u5e97\u94fa: {f1["\u5e97\u94fa\u540d\u79f0"].unique()[:5]}')

f2 = pd.read_excel(os.path.join(okdir, '\u6362\u7ed1\u6587\u4ef6_\u7b2c4\u6279.xlsx'), header=1)
print(f'\u65e7\u7b2c4\u6279 - \u5e97\u94fa: {f2["\u5e97\u94fa\u540d\u79f0"].unique()[:5]}')
