# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市三羊包装材料有限公司'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
sd = data[data['店铺名称'].str.strip() == shop_name].copy()

from collections import Counter

wb = oxl.load_workbook(r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx')
ws = wb.active

fail_skels = Counter()
fail_examples = []
for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    code = str(row[3] or '')
    if code == '定制链接':
        spec = str(sd.iloc[idx]['平台规格名称'] or '').strip()
        sk = re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', spec))[:300]
        fail_skels[sk] += 1
        if len(fail_examples) < 30:
            fail_examples.append((sk, spec[:150]))

print(f'总失败: {sum(fail_skels.values())}')
print()
for sk, cnt in fail_skels.most_common():
    ex = next((e[1] for e in fail_examples if e[0] == sk), '')
    print(f'  [{cnt}] {sk}')
    print(f'      例: {ex}')
