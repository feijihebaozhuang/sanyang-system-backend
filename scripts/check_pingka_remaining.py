# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 搜这些关键词
checks = {
    '优质进口纸-黄色 37*14': 0,
    '双白色 37*14': 0,
    '双面纯色 37*14': 0,
    '天猫止合': 0,
    '天猫扣底盒': 0,
    '天猫彩色 宽度:高度': 0,
}

for r in rows:
    if not r: continue
    n = str(r[3] or '').strip()
    s = str(r[0] or '').strip()
    
    if '优质进口纸-黄色' in n and '37*14' in n: checks['优质进口纸-黄色 37*14'] += 1
    if '双白色' in n and '37*14' in n: checks['双白色 37*14'] += 1
    if '双面纯色' in n and '37*14' in n: checks['双面纯色 37*14'] += 1
    if '止合' in s: checks['天猫止合'] += 1
    if '扣底盒' in s: checks['天猫扣底盒'] += 1
    if '彩色' in s and '宽度' in n and '高度' in n: checks['天猫彩色 宽度:高度'] += 1

for k, v in checks.items():
    print(f"{k}: {v}条")
