# -*- coding: utf-8 -*-
"""看看剩下的解析失败的数据是什么格式"""
import openpyxl, sys, re
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fp = r"d:\Desktop\换绑输出\未匹配平台商品.xlsx"
wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
ws = wb['Sheet1']

failed_samples = []
no_match_samples = []
other_count = Counter()

for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
    shop, pid, spec_id, spec_name, reason = row
    if not spec_name:
        continue
    s = str(spec_name).strip()
    if '解析失败' in str(reason):
        if len(failed_samples) < 50:
            failed_samples.append(s)
        # 归类
        if '【' in s:
            other_count['有【】'] += 1
        if '长度' in s:
            other_count['有长度'] += 1
        if '长' not in s and '宽' not in s and '高' not in s and '厚' not in s:
            other_count['无长宽高字眼'] += 1
        # 量词格式
        if re.search(r'\d+\s*[xX*×]\s*\d+', s):
            other_count['X格式尺寸'] += 1
        if '颜色' in s:
            other_count['有颜色'] += 1
    elif '无匹配编码' in str(reason):
        if len(no_match_samples) < 20:
            no_match_samples.append(s)

wb.close()

print(f"解析失败样本（前50）:")
for s in failed_samples:
    print(f"  [{other_count.get('有长度','?')}] {s[:80]}")

print(f"\n无匹配编码样本:")
for s in no_match_samples:
    print(f"  -> {s[:60]}")
