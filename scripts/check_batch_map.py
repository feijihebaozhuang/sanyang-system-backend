# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'
outdir = r'D:\Desktop\换绑输出'

# OK文件已有序号1-32
# 换绑输出新生成的是第1-14批（其中第1-7批在OK文件中已同名存在）
# 所以新批次为第8-14批，对应OK文件的第33-39批
# 但还要检查换绑输出/第1-7批内容和OK文件/第1-7批是否相同（同是友尚前的历史数据）

for batch in ['8','9','10','11','12','13','14']:
    src = os.path.join(outdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279.xlsx')
    if os.path.exists(src):
        print(f'存在第{batch}批: {src}')
    # 检查拆分部分
    has_parts = False
    for f in os.listdir(outdir):
        if f'\u7b2c{batch}\u6279_' in f and f.endswith('.xlsx'):
            has_parts = True
            print(f'  拆分: {f}')
            break

print('\n--- 对应关系 ---')
print('OK文件已有: 1-32批')
print('新移入: 8批(fix_shop_names)=第33批, 9批(v4)=第34批, 10批(v5)=第35批, 11批(v6)=第36批, 12批(v7)=第37批, 13批(v8)=第38批, 14批(final)=第39批')
