# -*- coding: utf-8 -*-
"""分析平台商品的规格名称格式，提取所有不同模式"""
import openpyxl, sys, re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fp = r"d:\Desktop\平台商品.xlsx"
wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
ws = wb['报表1']

patterns = {}
total = 0
for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    shop, pid, spec_name, spec_id = row
    if not spec_name:
        continue
    total += 1
    s = str(spec_name).strip()
    # 按模式分类
    if '【' in s:
        pattern = '【】格式'
    elif '长' in s and '宽' in s and ('高' in s or '厚' in s):
        pattern = '长宽高'
    elif '长' in s and '宽' in s:
        pattern = '长宽'
    elif '宽' in s and '高' in s:
        pattern = '宽高'
    elif '直径' in s or '口径' in s:
        pattern = '直径'
    elif '内径' in s or '外径' in s:
        pattern = '内外径'
    elif '珍珠棉' in s or 'pe' in s.lower():
        pattern = '珍珠棉'
    elif '定制' in s or '定做' in s:
        pattern = '定制'
    else:
        pattern = '其他'
    
    patterns.setdefault(pattern, []).append(s[:80])
    if total >= 50000:
        break

print(f"总计扫描: {total}行")
for p, samples in sorted(patterns.items(), key=lambda x: -len(x[1])):
    print(f"\n【{p}】共{len(samples)}条")
    # 显示不同的样本（去重）
    seen = set()
    for s in samples:
        if s not in seen:
            seen.add(s)
            print(f"  -> {s}")
        if len(seen) >= 6:
            break

wb.close()
