# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 一次性展示每类的样本
def show_samples(df2, cond, label, limit=5):
    seen = set()
    cnt = 0
    for _, row in df2.iterrows():
        s = str(row['规格名称'])
        if cond(s) and s not in seen:
            seen.add(s)
            print(f'  [{label}] {s}')
            cnt += 1
            if cnt >= limit:
                break

print('=== ①优质牛卡 ===')
show_samples(df2, lambda s: '优质牛卡' in s, '优质牛卡', 3)

print('\n=== ②【内径尺寸】(mm格式) ===')
show_samples(df2, lambda s: '【内径尺寸】' in s and '双白' in s, '双白', 3)
show_samples(df2, lambda s: '【内径尺寸】' in s and '双白' not in s, '其他材料', 5)

print('\n=== ③【内径】直接 ===')
show_samples(df2, lambda s: '【内径】' in s, '内径', 5)

print('\n=== ④外尺寸/外径 ===')
show_samples(df2, lambda s: ('外尺寸' in s or '外径' in s) and '【长宽】' not in s, '外尺寸', 5)
show_samples(df2, lambda s: '外尺寸 【长宽】' in s, '外尺寸【长宽】', 3)

print('\n=== ⑤纸箱类(LxW cm【长宽】;Hcm 高【类型】) ===')
show_samples(df2, lambda s: '【长宽】' in s and '外尺寸' not in s, '纸箱', 5)

print('\n=== ⑥直接格式(xxx-数量*L*W*H) ===')
show_samples(df2, lambda s: re.search(r'-\d+个\*', s) or re.search(r'-\d+个x', s), '直接', 5)

print('\n=== ⑦特殊(长【L】cm；宽【W】cm) ===')
show_samples(df2, lambda s: '长【' in s and '宽【' in s, '长宽', 3)

print('\n=== ⑧外尺寸【长宽】多参数 ===')
show_samples(df2, lambda s: '外尺寸 【长宽】' in s and ('纸箱' in s or '飞机盒' in s), '外尺寸纸箱', 5)

print('\n=== ⑨长mm；【宽高】mm；材料 ===')
show_samples(df2, lambda s: '长' in s and 'mm' in s and '宽高' in s, 'mm宽高', 5)

print('\n=== ⑩外尺寸【】【长宽】缺左括号 ===')
show_samples(df2, lambda s: '长宽】' in s and '外尺寸' not in s and '【内径' not in s and '【长宽】' not in s, '缺括号', 5)
