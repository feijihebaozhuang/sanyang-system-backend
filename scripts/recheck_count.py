# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']

for shop in ['飞机盒小批量专卖店', '深圳市三羊包装材料有限公司']:
    cnt = len(data[data['店铺名称'].str.strip() == shop])
    print(f'{shop}: {cnt} 条')
