# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = [
    r'D:\Desktop\1-定制商品结构.txt',
    r'D:\Desktop\2-扣底盒商品结构.txt',
    r'D:\Desktop\3-双插盒商品结构.txt',
    r'D:\Desktop\4-三层纸箱商品结构.txt',
    r'D:\Desktop\4a-五层纸箱商品结构.txt',
]

for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    m1 = re.search(r'结构数: (\d+)', content)
    m2 = re.search(r'总商品数: (\d+)', content)
    name = fpath.split('\\')[-1]
    structs = int(m1.group(1)) if m1 else '?'
    items = int(m2.group(1)) if m2 else '?'
    print(f'{name}: {structs} 结构, {items} 条')
