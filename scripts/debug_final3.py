# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'

# 五层不是数字！
# 必须用【.+?层】而不是【\d+层】
pat = r'高(\d+)cm【(.+?)层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】'
m = re.search(pat, s)
print(f'm={m}')
if m:
    print(f'H={m.group(1)}, layer={m.group(2)}, L={m.group(3)}, W={m.group(4)}')
    
# 还有更多
tests = [
    '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个',
    '高12cm【三层】；长宽【29*15】;高12cm【三层】;长宽【29*15】',
    '高8cm【三层纸箱】；长宽【29*15】100个',
    '高12cm【五层纸箱】；长宽【40*39cm】50个',
    '高【12cm】【三层纸箱】；长宽【30*20cm】100个',
]
for t in tests:
    m = re.search(r'高(\d+)cm【(.+?)层[^】]*】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', t)
    if m:
        print(f'✅ H={m.group(1)}, layer={m.group(2)}, L={m.group(3)}, W={m.group(4)}')
    else:
        print(f'❌ {t[:40]}')
