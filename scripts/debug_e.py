# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '长34 CM；宽 26CM；高度12CM;长34 CM;宽 26CM;高度12CM'

m = re.search(r'长(\d+\.?\d*)\s*(CM|cm)[；;]\s*宽\s*(\d+\.?\d*)\s*cm[；;]\s*高度(\d+\.?\d*)\s*cm', s, re.IGNORECASE)
print('m:', m)

m2 = re.search(r'长(\d+)\s*CM[；;]\s*宽\s*(\d+)\s*CM[；;]\s*高度(\d+)\s*CM', s)
print('m2:', m2)

# 直接删掉所有空格试
s2 = s.replace(' ', '')
print('s2:', repr(s2))
m3 = re.search(r'长(\d+)CM[；;]宽(\d+)CM[；;]高度(\d+)CM', s2)
print('m3:', m3)
