# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '尺寸不足_待处理.xlsx'), data_only=True)
ws = wb['尺寸不足']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 看更多样式的样本
seen = set()
samples = []
for r in rows:
    name = str(r[3] or '').strip()[:80]
    if name not in seen:
        seen.add(name)
        samples.append((r, name))

print(f"不同样本数: {len(samples)}", flush=True)

# 分组看模式
categories = {}
for r, name in samples:
    # 提取类型特征
    if '宽度' in name and '高度' in name and '长度' in name:
        cat = '宽度：x---高度：y;白色 长度：z'
    elif '优质进口纸' in name:
        cat = '优质进口纸-xxx'
    elif '双白色' in name or '双面纯色' in name:
        cat = '双白色/双面纯色'
    elif '**' in name:
        cat = '含**'
    elif '.5' in name or '.0' in name:
        cat = '含小数'
    elif '双面白' in name:
        cat = '双面白'
    else:
        cat = '其他'
    categories.setdefault(cat, []).append((r, name))

for cat, items in sorted(categories.items()):
    print(f"\n【{cat}】共{len(items)}种")
    for r, name in items[:5]:
        print(f"  {name}")
