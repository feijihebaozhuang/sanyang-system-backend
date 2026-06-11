# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 检查1-6 文件中的pid
for fname in [
    r'D:\Desktop\1-定制商品结构.txt',
    r'D:\Desktop\2-扣底盒商品结构.txt',
    r'D:\Desktop\3-双插盒商品结构.txt',
    r'D:\Desktop\4-三层纸箱商品结构.txt',
    r'D:\Desktop\4a-五层纸箱商品结构.txt',
]:
    with open(fname, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*pid=(.+)', line)
            if m:
                pid = m.group(1).strip()
                if pid in ('5145118190894', '5145118190893', '4863776885263', '4772764692890', '4768923641932'):
                    print(f'pid={pid} 在 {fname} 中发现！')
                    # 显示上下文
                    print(f'  -> 行: {line.strip()}')
