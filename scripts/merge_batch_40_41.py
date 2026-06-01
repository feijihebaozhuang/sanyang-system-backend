# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

okdir = r'D:\Desktop\换绑输出\OK文件'

# 第40批和第41批合并去重
f40 = os.path.join(okdir, '换绑文件_第40批.xlsx')
f41 = os.path.join(okdir, '换绑文件_第41批.xlsx')

df40 = pd.read_excel(f40, skiprows=1) if os.path.exists(f40) else pd.DataFrame()
df41 = pd.read_excel(f41, skiprows=1) if os.path.exists(f41) else pd.DataFrame()

combined = pd.concat([df40, df41], ignore_index=True)
# 去重
combined = combined.drop_duplicates(subset=['商品编码'])
print(f'第40批: {len(df40)} 条')
print(f'第41批: {len(df41)} 条')
print(f'合并去重: {len(combined)} 条')

# 覆盖写入第41批
import openpyxl
combined.to_excel(f41, index=False, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码'])
wb = openpyxl.load_workbook(f41)
ws = wb.active
ws.insert_rows(1)
ws.cell(1, 2).value = '商品对应表'
wb.save(f41)

# 删除第40批
os.remove(f40)
print(f'✅ 第41批已更新: {len(combined)} 条 (含原第40批内容)')
print(f'✅ 第40批已删除')
