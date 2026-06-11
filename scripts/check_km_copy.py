# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'd:\Desktop\快麦商品 - 副本.xlsx'
if os.path.exists(f):
    xl = pd.ExcelFile(f)
    print('工作表:', xl.sheet_names)
    df = pd.read_excel(f, sheet_name='报表1', header=None)
    print('行数:', len(df), '列数:', df.shape[1])
    for i in range(min(8, len(df))):
        vals = [str(v)[:40] for v in list(df.iloc[i])]
        print(f'  行{i}: {vals}')
else:
    print('文件不存在:', f)
    # 看桌面有哪些快麦文件
    import glob
    for ff in glob.glob(r'd:\Desktop\快麦*'):
        print('  ', ff)
