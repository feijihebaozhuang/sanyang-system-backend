# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = [
    ('1-定制商品结构.txt', r'D:\Desktop\1-定制商品结构.txt'),
    ('1a-定制商品结构（补充）.txt', r'D:\Desktop\1a-定制商品结构（补充）.txt'),
    ('2-扣底盒商品结构.txt', r'D:\Desktop\2-扣底盒商品结构.txt'),
    ('3-双插盒商品结构.txt', r'D:\Desktop\3-双插盒商品结构.txt'),
    ('4-三层纸箱商品结构.txt', r'D:\Desktop\4-三层纸箱商品结构.txt'),
    ('4a-五层纸箱商品结构.txt', r'D:\Desktop\4a-五层纸箱商品结构.txt'),
    ('5-剩余商品结构.txt', r'D:\Desktop\5-剩余商品结构.txt'),
    ('6-不属于定制的60个结构.txt', r'D:\Desktop\6-不属于定制的60个结构.txt'),
]

total_s = 0
total_i = 0
for name, path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    m1 = re.search(r'结构数: (\d+)', content)
    m2 = re.search(r'总商品数: (\d+)', content)
    s = int(m1.group(1)) if m1 else 0
    i = int(m2.group(1)) if m2 else 0
    total_s += s
    total_i += i
    print(f'{name}: {s} 结构, {i} 条')

print(f'\n合计: {total_s} 结构, {total_i} 条')
print(f'原始商品所有格式: 1775 结构, 498090 条')

# 原始结构数
with open(r'D:\Desktop\原始商品所有格式.txt', 'r', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'不同格式（按店铺\+结构）: (\d+)', line)
        if m:
            orig_s = int(m.group(1))
            print(f'原始结构: {orig_s}')
            break

print(f'\n结构验证: 1+2+3+4+4a+5+6 = {total_s} (原始={orig_s})')
if total_s == orig_s:
    print('✅ 结构数正确！')
else:
    print(f'❌ 差 {abs(total_s - orig_s)}')

# 商品条数：1+1a+2+3+4+4a = 已分类部分
classified = 15855 + 2283 + 6477 + 399 + 4969 + 31228
print(f'\n已分类(1+1a+2+3+4+4a): {classified} 条')
print(f'5+6 剩余: {total_i - classified} 条')
