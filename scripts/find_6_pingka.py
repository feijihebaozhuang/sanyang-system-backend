# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

# 要处理的6条规格
specs_to_find = [
    '优质进口纸-黄色【100个】;37*14**3.8',
    '双白色【100个】;37*14**3.8', 
    '双面纯色【50个】黑&红;37*14**3.8',
    '优质进口纸-黄色   100个;40.12*7',
    '双白色  100个;40.12*7',
    '双面纯色【50个】黑&红;40.12*7',
]

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f"平卡总条数: {len(rows)}", flush=True)

# 找到这6条
found = []
for r in rows:
    name = str(r[3] or '').strip()
    for s in specs_to_find:
        if s in name:
            found.append((s, r))
            break

print(f"找到匹配条数: {len(found)}")
for s, r in found:
    print(f"  ID: {r[1]}, 规格: {r[3]}")
