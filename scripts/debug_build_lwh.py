# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '双面纯色【50个】黑色;【长度 13 厘米】【宽度 10 厘米】系列 外径 130x100x20 mm'
print(f'规格: {s}')
print()

# 6号格式: 【长度 L 厘米】【宽度 W 厘米】
m = re.search(r'【长度\s*([\d.]+)\s*厘米\s*】.*?【宽度\s*([\d.]+)\s*厘米\s*】', s)
print(f'【长度X厘米】【宽度Y厘米】: {m}')
if m:
    print(f'  长度={m.group(1)}, 宽度={m.group(2)}')

# 5号格式: 外径
m = re.search(r'外径[：:]*\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)(?:\s*mm)?', s)
print(f'外径: {m}')
if m:
    v = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    print(f'  原始: {v}')
    if any(x > 50 for x in v):
        v = [x/10 for x in v]
        print(f'  转cm后: {v}')
    else:
        print(f'  未转cm: {v}')

# 7号: 长前缀
m = re.search(r'[长L]+\s*[：:]?\s*(\d+\.?\d*)\s*(?:cm|mm)?\s*[xX*]\s*(\d+\.?\d*)\s*(?:cm|mm)?\s*[xX*]\s*(\d+\.?\d*)', s)
print(f'长前缀: {m}')

# 9号: 裸LxWxH
m = re.search(r'(?:^|[\s；;])(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)', s)
print(f'裸LxWxH: {m}')

print()

# 检查v7中的维度过滤
print('=== build_lwh 过滤 ===')
all_dims = []
# 手动模拟extract_all_dims返回
# 模拟正常的返回
def mock_extract(s):
    results = []
    m = re.search(r'【长度\s*([\d.]+)\s*厘米\s*】.*?【宽度\s*([\d.]+)\s*厘米\s*】', s)
    if m: results.append((float(m.group(1)), float(m.group(2)), 0, '长宽厘米'))
    m = re.search(r'外径[：:]*\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)(?:\s*mm)?', s)
    if m:
        v = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
        if any(x > 50 for x in v):
            v = [x/10 for x in v]
        results.append((v[0], v[1], v[2], '外径'))
    m = re.search(r'(?:^|[\s；;])(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)', s)
    if m: results.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), '裸'))
    return results

all_dims = mock_extract(s)
print(f'extract_all_dims结果: {all_dims}')
print()

# 模拟 build_lwh 的筛选
for l, w, h, src in all_dims:
    print(f'  检验 ({l},{w},{h},{src})...')
    if h > 0 and 0.5 <= l <= 200 and 0.5 <= w <= 200 and 0.5 <= h <= 200:
        print(f'    → 命中h>0条件: L={l} W={w} H={h}')
    else:
        print(f'    → 未命中h>0条件: h={h}, l={l}<=200={l<=200}, w={w}<=200={w<=200}, h={h}<=200={h<=200}')
