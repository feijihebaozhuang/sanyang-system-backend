# -*- coding: utf-8 -*-
import re

for fname in ['5-剩余商品结构.txt', '6-不属于定制的60个结构.txt']:
    red_structs = set()
    red_lines = 0
    with open(f'D:\\Desktop\\{fname}', 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*\[\d+\]\s*\[x\d+\]\s*结构:\s*(.+)', line)
            if m:
                sk = m.group(1).strip()
                if '红' in sk:
                    red_structs.add(sk)
                    red_lines += 1
    print(f'{fname}: 含"红"结构 {len(red_structs)} 个, 含"红"行 {red_lines} 行')
    for sk in sorted(red_structs):
        print(f'    {sk}')
