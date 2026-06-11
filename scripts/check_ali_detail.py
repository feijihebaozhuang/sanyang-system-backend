# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 看看友尚在定制文件里的完整数据
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '定制类_换绑文件.xlsx'), data_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(min_row=3, values_only=True))
wb.close()

print("阿里友尚的完整数据:")
for r in rows:
    if '友尚' in str(r[0]):
        print(f"  商品ID: {r[1]:20s}  规格ID: {r[2]:50s}  编码: {r[3]}")
        break

print("\n阿里新鑫星的完整数据:")
for r in rows:
    if '新鑫星' in str(r[0]):
        print(f"  商品ID: {r[1]:20s}  规格ID: {r[2]:50s}  编码: {r[3]}")
        break

# 再查一下友尚这条在原始数据里到底是什么
import pandas as pd
pf = r'd:\Desktop\平台商品.xlsx'
df = pd.read_excel(pf, sheet_name='报表1', header=2, dtype=str)

# 查 535958072829 这个商品ID
ys_rows = df[df.iloc[:, 1].astype(str).str.contains('535958072829', na=False)]
print(f"\n\n阿里友尚 商品ID=535958072829 的完整规格:")
for idx, row in ys_rows.head(3).iterrows():
    print(f"  商品ID: {row.iloc[1]}")
    print(f"  规格名: {str(row.iloc[2])[:80]}")
    print(f"  规格ID: {row.iloc[3]}")
    print()
