# -*- coding: utf-8 -*-
"""显示品牌店911条全部情况，按模式分组"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]

print("=" * 60)
print("一、模式A：（宽）X mm 外径;【100个】长度 Y mm;Z mm [后缀]")
print("   共668条，尺寸单位mm")
print("=" * 60)

specs_a = Counter()
for r in pp:
    spec = str(r[3] or '').strip()
    m = re.search(r'（宽）(\d+\.?\d*)\s*mm\s*外径.*?长度\s*(\d+\.?\d*)\s*mm\s*;\s*(\d+\.?\d*)\s*mm?\s*(.*)', spec)
    if m:
        w = float(m.group(1))
        l = float(m.group(2))
        h = float(m.group(3))
        suffix = m.group(4).strip() or '(无后缀)'
        key = (w, l, h, suffix)
        specs_a[key] += 1

for (w, l, h, suffix), cnt in sorted(specs_a.items(), key=lambda x: (-x[1], x[0])):
    # 外径cm
    w_cm = w/10
    l_cm = l/10
    h_cm = h/10
    # 你说的外径→内径规则: 长-1.5, 宽-0.5, 高-0.5
    # 但这里宽=长，所以按你说的13.5→12 13 10
    # 即：长-1.5, 宽-0.5, 高-0.5 然后排序
    il, iw, ih = l_cm-1.5, w_cm-0.5, h_cm-0.5
    expect = f"长{l_cm}*宽{w_cm}*高{h_cm} → 内径 {il:.1f}*{iw:.1f}*{ih:.1f}"
    mat = '白色' if '双面白' in suffix or '白色' in suffix else '特硬'
    print(f"  [{cnt}条] 宽{w}mm 长{l}mm 高{h}mm 后缀={suffix}")
    print(f"          → 外径{l_cm}*{w_cm}*{h_cm}  → 期望编码: {int(il)}*{int(iw)}*{int(ih)}-内径-{mat}")

print()
print("=" * 60)
print("二、模式B：进口优质特硬E瓦-内径/外经（2条）")
print("=" * 60)
for r in pp:
    spec = str(r[3] or '').strip()
    if '进口优质' in spec:
        # 提取尺寸
        m = re.search(r'长x宽[【】\s]*(\d+)x(\d+)', spec)
        h_m = re.search(r'(\d+)mm【高】', spec)
        if m and h_m:
            x = int(m.group(1)) / 10
            y = int(m.group(2)) / 10
            h = int(h_m.group(1)) / 10
            dk = '内径' if '内径' in spec else '外径'
            print(f"  {spec}")
            print(f"  → 尺寸: {x}*{y}*{h} {dk} 特硬")

print()
print("=" * 60)
print("三、模式C：【材料】外径;【XxY】;Z cm高度（243条）")
print("=" * 60)
specs_c = Counter()
for r in pp:
    spec = str(r[3] or '').strip()
    m = re.search(r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度', spec)
    if m:
        mat = m.group(1).strip()
        dk = m.group(2).strip()
        x = float(m.group(3))
        y = float(m.group(4))
        h = float(m.group(5))
        # 材料映射
        mat_map = {'双面白色': '白色', '台湾纸': '超硬', '特硬原色': '特硬'}
        out_mat = mat_map.get(mat, '特硬')
        print(f"  【{mat}】{dk} {int(x)}x{int(y)}x{int(h)}cm")
        print(f"      → 编码: {int(x)}*{int(y)}*{int(h)}-{dk}-{out_mat}")

print()
print("=" * 60)
print("汇总")
print("=" * 60)
total = sum(specs_a.values()) + 2 + sum(1 for r in pp if re.search(r'【[^】]*】\s*(内径|外径)\s*;', str(r[3] or '')))
print(f"  模式A: {sum(specs_a.values())}条")
print(f"  模式B: 2条")
print(f"  模式C: {sum(1 for r in pp if re.search(r'【[^】]*】\s*(内径|外径)\s*;', str(r[3] or '')))}条")
print(f"  合计: {total}条")
