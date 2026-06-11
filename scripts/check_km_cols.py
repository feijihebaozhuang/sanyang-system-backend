# -*- coding: utf-8 -*-
import sys, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
df = pd.read_excel(r'd:\Desktop\换绑输出\快麦商品.xlsx')
print(list(df.columns))
