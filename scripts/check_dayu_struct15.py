# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市大鱼包装材料有限公司'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# 结构15
sk_target = 'N个长宽N*N；高N【N层】;N个长宽N*N;高N【N层】'

pids = set()
specs = set()
for idx in range(len(shop_data)):
    row = shop_data.iloc[idx]
    spec = str(row['平台规格名称'] or '').strip()
    pid = str(row['平台商品id'] or '').strip()
    if make_skeleton(spec) == sk_target:
        pids.add(pid)
        specs.add(spec)

print(f'结构15 共 {len(pids)} 条')
print(f'不同PID数: {len(pids)}')
print(f'不同规格样例数: {len(specs)}')
print()
print('=== PID 列表（给你核实）===')
for pid in sorted(pids)[:20]:
    print(f'  pid={pid}')
if len(pids) > 20:
    print(f'  ... 共 {len(pids)} 个不同PID')
print()
print('=== 规格样例 ===')
for s in sorted(specs)[:5]:
    print(f'  {s}')
