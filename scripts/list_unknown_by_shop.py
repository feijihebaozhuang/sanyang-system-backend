# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
print('读取中...')
df = pd.read_excel(source, dtype=str)
print(f'总行数: {len(df)}')

# 第0行是标题行，第1行是列名，数据从第2行开始
# 但pandas已经把第0行当标题了，检查一下
# 实际上列名是: 店铺名称, 平台商品id, 平台规格名称, 平台规格id

shop_col = 'Unnamed: 0'
sku_col = 'Unnamed: 2'

# 跳过标题行(第0行是"店铺名称"等)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
print(f'有效数据行: {len(data)}')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

# 按店铺分组
shop_groups = defaultdict(lambda: defaultdict(int))
shop_spec_examples = defaultdict(dict)  # shop -> {sk: spec}

for idx in range(len(data)):
    row = data.iloc[idx]
    shop = str(row['店铺名称'] or '').strip()
    spec = str(row['平台规格名称'] or '').strip()
    pid = str(row['平台商品id'] or '').strip()
    spec_id = str(row['平台规格id'] or '').strip()
    if not spec or not shop:
        continue
    sk = make_skeleton(spec)
    shop_groups[shop][sk] += 1
    if sk not in shop_spec_examples[shop]:
        shop_spec_examples[shop][sk] = (spec, pid, spec_id)

# 输出到文件
outpath = r'D:\Desktop\未识别飞机盒_待分析_按店铺.txt'
shop_order = sorted(shop_groups.keys(), key=lambda sh: sum(shop_groups[sh].values()), reverse=True)

with open(outpath, 'w', encoding='utf-8') as f:
    f.write(f'总行数: {len(data)}, 总店铺数: {len(shop_groups)}\n\n')
    total_structs = 0
    for shop in shop_order:
        items = shop_groups[shop]
        shop_total = sum(items.values())
        sk_list = sorted(items.keys(), key=lambda x: -items[x])
        total_structs += len(sk_list)
        f.write(f'═══ {shop}（{len(sk_list)} 种格式, 共 {shop_total} 条）═══\n')
        for i, sk in enumerate(sk_list, 1):
            cnt = items[sk]
            spec_example, pid, spec_id = shop_spec_examples[shop][sk]
            f.write(f'  [{i}] [x{cnt}] {sk}\n')
            f.write(f'       例: {spec_example}\n')
            f.write('\n')
        f.write('\n')
    f.write(f'\n汇总: {len(shop_groups)} 店铺, {total_structs} 结构, {len(data)} 条\n')

print(f'✅ 已生成: {outpath}')
print(f'店铺数: {len(shop_groups)}, 总结构数: {total_structs}')
