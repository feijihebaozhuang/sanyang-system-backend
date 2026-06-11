# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()

# 取第1条
row = target.iloc[0]
spec = str(row['规格名称'])
print(f'spec = {repr(spec[:100])}')
print(f'len = {len(spec)}')
print(f'高 = {spec.find("高")}')
print(f'【 = {spec.find("【")}')
print(f'； = {spec.find("；")}')
print(f'长 = {spec.find("长")}')
for i, ch in enumerate(spec[:30]):
    print(f'  [{i}]: U+{ord(ch):04X} ({ch})')

# 直接测试
s = spec
pat = r'高(\d+)cm【\d+层】'
m = re.search(pat, s)
if m: print(f'✅ match: H={m.group(1)}')
else: print('❌ no match for 高pattern')

m2 = re.search(r'长宽【(\d+)\*(\d+)】', s)
if m2: print(f'✅ match: L={m2.group(1)}, W={m2.group(2)}')
else: print('❌ no match for 长宽pattern')
