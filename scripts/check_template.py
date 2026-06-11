# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'
files = sorted([f for f in os.listdir(okdir) if f.endswith('.xlsx') and '\u5df2\u4e0a\u4f20' not in f])
for f in files[:3]:
    df = pd.read_excel(os.path.join(okdir, f))
    print(f'{f}: \u5217={list(df.columns)}, \u884c={len(df)}')

print('---')
outdir = r'D:\Desktop\换绑输出'
for f in sorted(os.listdir(outdir)):
    if not f.endswith('.xlsx') or '\u90e8\u5206' in f: continue
    if '\u6362\u7ed1' not in f: continue
    df = pd.read_excel(os.path.join(outdir, f))
    print(f'{f}: \u5217={list(df.columns)}, \u884c={len(df)}')
