# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'

# 测试【】
p1 = r'【\d+层】'
m1 = re.search(p1, s)
if m1:
    print(f'found: {m1.group()}')
else:
    print('Cannot find 【digits层】')

# 试试不用【】，用\u3010
p2 = r'\u3010\d+层\u3011'
m2 = re.search(p2, s)
if m2:
    print(f'found2: {m2.group()}')
else:
    print('Cannot find u3010 pattern')

# 尝试直接字符类
for i, c in enumerate(s[:20]):
    print(f'  [{i}]: {c} U+{ord(c):04X}', end='')
    if c in '\u3010\u3011':
        print(' ***')
    else:
        print()
