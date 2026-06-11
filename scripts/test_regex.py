# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 测试正则是否匹配 高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个
tests = [
    '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个',
    '高13cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个',
    '高12cm【五层】；长宽【29*15】;高12cm【五层】;长宽【29*15】',
    '高12cm【五层】；长宽【29*15】',
]

pat = r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】'

for s in tests:
    m = re.search(pat, s)
    if m:
        print(f'✅ 匹配: {s}')
        print(f'   H={m.group(1)}, L={m.group(2)}, W={m.group(3)}')
    else:
        print(f'❌ 未匹配: {s}')

# 试另一个pattern
print('\n--- 尝试不同分隔符 ---')
pat2 = r'高(\d+)cm【\d+层】[^；;]*[；;]\s*长宽【([\d.]+)\*([\d.]+)】'

pat3 = r'高(\d+)cm【\d+层】[^；;]*?长宽【([\d.]+)\*([\d.]+)】'

for s in tests:
    for pi, pat in enumerate([pat2, pat3]):
        m = re.search(pat, s)
        if m:
            print(f'P{pi+1} ✅: {s[:40]}... H={m.group(1)}, L={m.group(2)}, W={m.group(3)}')
            break
    else:
        print(f'❌: {s[:50]}')
