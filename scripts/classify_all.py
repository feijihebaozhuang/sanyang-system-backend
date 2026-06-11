# -*- coding: utf-8 -*-
"""直接从平台商品表分析所有【】格式+无长宽高 和其他类别的样本"""
import openpyxl, sys, re
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fp = r"d:\Desktop\平台商品.xlsx"
wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
ws = wb['报表1']

cats = {
    'A-【】+有长宽高': [],
    'B-【】+无长宽高': [],
    'C-有长宽高+无【】': [],
    'D-纯数字/符号': [],
    'E-其他': [],
}

for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    shop, pid, spec_name, spec_id = row
    if not spec_name:
        continue
    s = str(spec_name).strip()
    
    # 分类
    has_kw = '长' in s or '宽' in s or '高' in s or '厚度' in s or '长度' in s
    has_bracket = '【' in s
    
    if has_bracket and has_kw:
        cat = 'A-【】+有长宽高'
    elif has_bracket:
        cat = 'B-【】+无长宽高'
    elif has_kw:
        cat = 'C-有长宽高+无【】'
    elif re.match(r'^[\d\.\-\sxX*×/]+$', s) or not re.search(r'[\u4e00-\u9fff]', s):
        cat = 'D-纯数字/符号'
    else:
        cat = 'E-其他'
    
    if len(cats[cat]) < 50:
        cats[cat].append(s)

wb.close()

for cat, samples in cats.items():
    print(f"\n{'='*60}")
    print(f"【{cat}】共{len(samples)}个样本")
    print(f"{'='*60}")
    for s in samples:
        print(f"  -> {s[:90]}")
