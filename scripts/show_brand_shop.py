# -*- coding: utf-8 -*-
"""显示品牌店911条的具体情况，让用户告诉处理规则"""
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
print("模式A：（宽）X mm 外径;【100个】长度 X mm;Y mm [后缀]")
print("=" * 60)
specs_a = Counter()
details_a = []
for r in pp:
    spec = str(r[3] or '').strip()
    m = re.search(r'（宽）(\d+\.?\d*)\s*mm\s*外径.*?长度\s*(\d+\.?\d*)\s*mm\s*;\s*(\d+\.?\d*)\s*mm?\s*(.*)', spec)
    if m:
        w = float(m.group(1))
        l = float(m.group(2))
        h = float(m.group(3))
        suffix = m.group(4).strip() or '(无后缀)'
        key = f'宽{w}mm 长{l}mm 高{h}mm [{suffix}]'
        specs_a[key] += 1
        details_a.append((w, l, h, suffix, spec))

print(f"共 {len(details_a)} 条")
for k, v in sorted(specs_a.items(), key=lambda x: (-x[1], x[0])):
    print(f"  [{v}条] {k}")

print()
print("=" * 60)
print("模式B：进口优质特硬E瓦-内径/外经")
print("=" * 60)
for r in pp:
    spec = str(r[3] or '').strip()
    if '进口优质' in spec:
        print(f"  {spec}")

print()
print("=" * 60)
print("模式C：【材料】内径/外径;【XxY 】;Z cm高度")
print("=" * 60)
specs_c = Counter()
for r in pp:
    spec = str(r[3] or '').strip()
    m = re.search(r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度', spec)
    if m:
        mat_ctx = m.group(1).strip()
        dk = m.group(2)
        x = m.group(3)
        y = m.group(4)
        h = m.group(5)
        key = f'材料[{mat_ctx}] {dk} {x}x{y}x{h}cm'
        specs_c[key] += 1

print(f"共 {sum(specs_c.values())} 条")
for k, v in sorted(specs_c.items(), key=lambda x: (-x[1], x[0])):
    print(f"  [{v}条] {k}")

print()
print("=" * 60)
print("总结")
print("=" * 60)
print(f"  模式A: {len(details_a)} 条")
print(f"  模式B: 2 条")
print(f"  模式C: {sum(specs_c.values())} 条")
print(f"  合计: {len(details_a) + 2 + sum(specs_c.values())} 条")

# 打印模式A的详细样本（每个变体1条）
print("\n\n模式A样本（无后缀 + 双面白后缀各一条）：")
for r in pp:
    spec = str(r[3] or '').strip()
    if '进口优质' in spec or '【' in spec: 
        continue
    m = re.search(r'（宽）(\d+\.?\d*)\s*mm', spec)
    if m:
        w = float(m.group(1))
        h = re.search(r';(\d+\.?\d*)\s*mm', spec)
        h_val = h.group(1) if h else '?'
        suffix = spec.split('mm')[1] if 'mm' in spec else ''
        suffix_clean = suffix.strip()
        if suffix_clean:
            print(f"  {spec[:120]}")
    break
