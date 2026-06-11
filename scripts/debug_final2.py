# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 这就是之前说"no 高pattern"的正则
pat = r'高\d+cm【\d+层】'
m = re.search(pat, '高12cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个')
print(f'm={m}')
if m: print(f'match={m.group()}')

# 这是完整的
pat2 = r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】'
s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'
m2 = re.search(pat2, s)
print(f'm2={m2}')
if m2: print(f'H={m2.group(1)},L={m2.group(2)},W={m2.group(3)}')
else:
    # 分解看哪步失败
    for part in ['高', '12', 'cm', '【', '五', '层', '】', '；', '长']:
        if part not in s:
            print(f'MISSING: {part}')
    # 检查[^；;]*匹配了什么
    m_h = re.search(r'高(\d+)cm', s)
    m_end = re.search(r'长宽【([\d.]+)\*([\d.]+)】', s)
    print(f'H match: {m_h.group() if m_h else "NO"}')
    print(f'LW match: {m_end.group() if m_end else "NO"}')
    # 看中间部分
    if m_h and m_end:
        between = s[m_h.end():m_end.start()]
        print(f'between: [{repr(between)}]')
        print(f'contains ；: {"；" in between}')
