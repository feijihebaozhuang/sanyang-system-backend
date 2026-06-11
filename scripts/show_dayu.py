# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd, re
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('大鱼', na=False)
df2 = df[mask]

print('=== 阿里大鱼 %d条 ===\n' % len(df2))

# 归类
cats = {}
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    cat = '其他'
    
    if re.search(r'外径.*?高.*?；?长x宽', s) or re.search(r'长x宽.*?；.*?高', s):
        cat = '外径长宽高'
    elif re.search(r'外径.*?【.*?】', s):
        cat = '外径【】'
    elif re.search(r'外尺寸', s):
        cat = '外尺寸'
    elif re.search(r'内径', s):
        cat = '内径'
    elif re.search(r'内尺寸', s):
        cat = '内尺寸'
    elif re.search(r'纸箱.*?层', s):
        cat = '纸箱多层'
    elif re.search(r'扣底盒|双插盒', s):
        cat = '扣底盒/双插盒'
    elif re.search(r'长\d+', s):
        cat = '有长字'
    elif re.search(r'宽\d+', s):
        cat = '有宽字'
    elif re.search(r'高\d+', s):
        cat = '有高字'
    
    if cat not in cats: cats[cat] = []
    cats[cat].append(s)

for k, v in sorted(cats.items(), key=lambda x: -len(x[1])):
    print('\n=== %s: %d条 ===' % (k, len(v)))
    # 去重展示
    seen = set()
    for s in v:
        if s not in seen:
            seen.add(s)
            print('  %s' % s)
            if len(seen) >= 15:
                print('  ... 还有%d条' % (len(v) - len(seen)))
                break
