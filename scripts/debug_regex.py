# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'

pat = r'高'
m = re.search(pat, s)
print(f'√: 找到"高" at pos {m.start()}') if m else print('Cannot find 高')

pat2 = r'\u9AD8'
m2 = re.search(pat2, s)
print(f'√: 找到\\u9AD8 at pos {m2.start()}') if m2 else print('Cannot find \\u9AD8')

pat3 = re.compile(r'高12')
m3 = pat3.search(s)
print(f'√: 找到"高12" at pos {m3.start()}') if m3 else print('Cannot find 高12')

# 可能文件不是UTF-8?
import locale
print(f'locale={locale.getpreferredencoding()}')

# 试试
s2 = '高12cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个'
m4 = re.search(r'高(\d+)cm', s2)
print(f're.search high: {m4.group(1)}') if m4 else print('no')

m5 = re.search(r'高\d+cm【\d+层】', s2)
print(f'高pattern: {m5.group()}') if m5 else print('no 高pattern')

# 试试编译
pat_full = re.compile(r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【(\d+)\*(\d+)】')
m6 = pat_full.search(s)
if m6: print(f'full-match: H={m6.group(1)}, L={m6.group(2)}, W={m6.group(3)}')
else:
    # 分段
    h_m = re.search(r'高(\d+)cm', s)
    lw_m = re.search(r'长宽【(\d+)\*(\d+)】', s)
    if h_m and lw_m:
        print(f'分段: H={h_m.group(1)}, L={lw_m.group(1)}, W={lw_m.group(2)}')
