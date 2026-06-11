# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

tests = [
    '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个',
    '高13cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个',
    '高12cm【五层】；长宽【29*15】;高12cm【五层】;长宽【29*15】',
    '高12cm【五层】；长宽【29*15】',
]

# 最简单的方式
pat = r'高(\d+)cm【\d+层】'
for s in tests:
    m_h = re.search(pat, s)
    m_lw = re.search(r'长宽【(\d+)\*(\d+)】', s)
    if m_h and m_lw:
        print(f'✅ H={m_h.group(1)}, L={m_lw.group(1)}, W={m_lw.group(2)}')
    else:
        print(f'❌')
