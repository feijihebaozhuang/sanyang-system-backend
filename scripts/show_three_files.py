# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

d = r'D:\Desktop\换绑输出'
files = [f for f in os.listdir(d) if f.endswith('.xlsx') and not f.startswith('~$')]

targets = ['未匹配', '无匹配', '换绑文件']
for fn in sorted(files):
    for t in targets:
        if t in fn:
            p = os.path.join(d, fn)
            df = pd.read_excel(p)
            print(f'=== {fn} ===')
            print(f'  列: {list(df.columns)}')
            print(f'  行数: {len(df)}')
            print(f'  前2行:')
            for _, r in df.head(2).iterrows():
                vals = [str(x)[:40] for x in r.values]
                print(f'    {vals}')
            print()
            break
