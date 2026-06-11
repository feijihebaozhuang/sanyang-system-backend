# -*- coding: utf-8 -*-
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

# 找快麦文件
flist = glob.glob(r'd:\Desktop\换绑输出\快麦*.xlsx') + glob.glob(r'd:\Desktop\快麦*.xlsx')
print('找到快麦文件:', flist)

if flist:
    df = pd.read_excel(flist[0])
    cols = list(df.columns)
    print('列名:', cols)
    print('前2行:')
    print(df.head(2).to_dict(orient='records'))
else:
    # 找目录下所有xlsx
    flist2 = glob.glob(r'd:\Desktop\*.xlsx')
    print('桌面xlsx:', flist2)
    flist3 = glob.glob(r'd:\Desktop\换绑输出\*.xlsx')
    print('换绑输出xlsx:', [os.path.basename(f) for f in flist3])
