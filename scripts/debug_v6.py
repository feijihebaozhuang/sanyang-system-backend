# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'

# 找平卡文件
files = os.listdir(OUT_DIR)
pingka_file = [f for f in files if f.startswith('\u5e73') and f.endswith('.xlsx')]
print(f'Found files: {pingka_file}')
if not pingka_file: 
    print('All files:', files[:20])
    exit()
    
PINGKA = os.path.join(OUT_DIR, pingka_file[0])
df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
samples = target['规格名称'].dropna().astype(str).str.strip().tolist()

pat_fb1 = re.compile(r'高(\d+)cm【(.+?)层[^】]*】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】')

for i, s in enumerate(samples[:30]):
    m = pat_fb1.search(s)
    if m:
        print(f'{i+1} ✅ H={m.group(1)}, L={m.group(3)}, W={m.group(4)}')
    else:
        m2 = re.search(r'高(\d+)cm', s)
        m3 = re.search(r'长宽【(\d+)\*(\d+)】', s)
        m4 = re.search(r'【(.+?)层[^】]*】', s)
        if m2 and m3:
            mid = s[m2.end():m3.start()]
            print(f'{i+1} ❌ H={m2.group(1)} mid={repr(mid[:40])} 层match={m4.group(0) if m4 else "NO"}')
        else:
            print(f'{i+1} ?? {s[:60]}')
