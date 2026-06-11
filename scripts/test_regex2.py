# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

tests = [
    '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个',
    '高13cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个',
    '高12cm【五层】；长宽【29*15】;高12cm【五层】;长宽【29*15】',
    '高12cm【五层】；长宽【29*15】',
]

for s in tests:
    m = re.search(r'高(\d+)cm【\d+层】(?:[^；;]*|[^；;]*[；;]\d+个)[；;]长宽【(\d+)\*(\d+)】', s)
    if m:
        print(f'✅ H={m.group(1)}, L={m.group(2)}, W={m.group(3)}')
    else:
        # 试试更简单的
        m2 = re.search(r'(高\d+cm【\d+层】).*?长宽【(\d+)\*(\d+)】', s)
        if m2:
            h = int(re.search(r'高(\d+)', m2.group(1)).group(1))
            print(f'✅ H={h}, L={m2.group(2)}, W={m2.group(3)}')
        else:
            print(f'❌')
