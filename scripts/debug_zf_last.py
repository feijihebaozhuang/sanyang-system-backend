# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '长宽19x19 cm；8cm 内径'
m = re.search(r'长宽(\d+)x(\d+)\s*cm[^;]*[；;]\s*(\d+)cm内径', s)
print('m1:', m)

m2 = re.search(r'长宽(\d+)x(\d+)\s*cm[^；;]*[；;]\s*(\d+)\s*cm\s*内径', s)
print('m2:', m2)

# 看看字符
for i, ch in enumerate(s):
    print('U+%04X' % ord(ch), end=' ')
    if i % 5 == 4: print()
print()
