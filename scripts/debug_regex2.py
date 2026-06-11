# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'

# 测试【】
p1 = r'【\d+层】'
m1 = re.search(p1, s)
if m1: print(f'√: found "{m1.group()}"') 
else: print('Cannot find 【digits层】')

# 逐个字符
for i, c in enumerate(s):
    if c in '【】':
        print(f'c[{i}] = {c} U+{ord(c):04X}')

# 试试构建
p2 = '[\\u3010]'
m2 = re.search(p2, s)
if m2: print(f'√: found by \\u3010') else: print('Cannot find \\u3010')
