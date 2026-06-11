# -*- coding: utf-8 -*-
"""精确显示品牌店911条在每个正则下的分类"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'

# 从 batch_pp.py 复制正则和逻辑
RE_M2 = re.compile(r'[（(]宽[）)]\s*(\d+\.?\d*)\s*mm?\s*外径\s*;\s*长度\s*(\d+\.?\d*)\s*mm?\s*;\s*(\d+\.?\d*)\s*mm?\s*(.*)')
RE_M10 = re.compile(r'进口优质.*?内径\s*;\s*长x宽[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm?[】]*\s*;\s*(\d+\.?\d*)\s*mm?')
RE_M14 = re.compile(r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度')

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]
print(f"\n品牌店总条数: {len(pp)}")

m2_ok = []; m10_ok = []; m14_ok = []; other = []
for r in pp:
    spec = str(r[3] or '').strip()
    if RE_M2.search(spec):
        m2_ok.append(r)
    elif RE_M10.search(spec):
        m10_ok.append(r)
    elif RE_M14.search(spec):
        m14_ok.append(r)
    else:
        other.append(r)

print(f"  模式A (RE_M2 宽): {len(m2_ok)}")
print(f"  模式B (RE_M10 进口优质): {len(m10_ok)}")
print(f"  模式C (M14 【】内径/外径): {len(m14_ok)}")
print(f"  其他: {len(other)}")

if other:
    print(f"\n--- 无法匹配的 {len(other)} 条 ---")
    for i, r in enumerate(other[:50]):
        spec = str(r[3] or '').strip()
        print(f"  {i+1}. {spec[:150]}")
else:
    print(f"\n全部911条都能被正则匹配，没有遗漏。")

# 模式A详情
print(f"\n{'='*60}")
print(f"模式A详情：（宽）X mm 外径;长度 X mm;Y mm [后缀]")
print(f"{'='*60}")
specs_a = Counter()
for r in m2_ok:
    spec = str(r[3] or '').strip()
    m = RE_M2.search(spec)
    w = float(m.group(1))
    l = float(m.group(2))
    h = float(m.group(3))
    suffix = m.group(4).strip() if m.group(4) else '(无)'
    key = f"宽{w}mm 长{l}mm 高{h}mm [{suffix}]"
    specs_a[key] += 1
for k, v in sorted(specs_a.items(), key=lambda x: (-x[1], x[0])):
    print(f"  [{v}条] {k}")

# 模式C详情
print(f"\n{'='*60}")
print(f"模式C详情：【材料】内/外径;【XxY】;Z cm高度")
print(f"{'='*60}")
specs_c = Counter()
for r in m14_ok:
    spec = str(r[3] or '').strip()
    m = RE_M14.search(spec)
    mat = m.group(1).strip()
    dk = m.group(2).strip()
    x = m.group(3)
    y = m.group(4)
    h = m.group(5)
    key = f"[{mat}] {dk} {x}x{y}x{h}cm"
    specs_c[key] += 1
for k, v in sorted(specs_c.items(), key=lambda x: (-x[1], x[0])):
    print(f"  [{v}条] {k}")
