# -*- coding: utf-8 -*-
"""
深度抽样检查 - 对每个店铺展示 规格名 → 商品编码 的实际转换样例
按不同的 skel（骨架）类型各抽几条，让你可以直观检查准确性
"""
import sys, re, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

SOURCE = r'D:\Desktop\未识别飞机盒_待分析.xlsx'

def ms(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

print('读取源数据...')
df = pd.read_excel(SOURCE, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店', '商品id', '规格名', '规格id']
data['店'] = data['店'].str.strip()
data = data[data['店'] != '店铺名称']

# 按店铺逐个检查
for shop_name in sorted(data['店'].unique()):
    sd = data[data['店'] == shop_name].copy()
    total = len(sd)
    
    safe = shop_name.replace('/', '_').replace('\\', '_').replace(':', '_')
    fp = os.path.join(r'D:\Desktop', f'换绑_{safe}.xlsx')
    
    if not os.path.exists(fp):
        print(f'\n{"="*60}')
        print(f'【{shop_name}】文件不存在!')
        continue
    
    # 读取生成文件
    gen = pd.read_excel(fp, dtype=str)
    gen = gen.iloc[2:].copy()
    gen.columns = ['店铺名称', '平台商品id', '平台规格id', '商品编码']
    
    # 按skel分组取样本
    sd['skel'] = sd['规格名'].apply(ms)
    skel_groups = sd.groupby('skel').size().sort_values(ascending=False)
    
    print(f'\n{"="*60}')
    print(f'【{shop_name}】共 {total} 条, {len(skel_groups)} 种格式')
    print(f'{"="*60}')
    
    # 统计编码类型
    codes = gen['商品编码'].str.strip()
    custom = (codes == '定制链接').sum()
    resolved = len(codes) - custom
    eb = codes.str.contains('-EB|-3B', na=False).sum()
    pct = resolved / max(len(codes), 1) * 100
    print(f'解析成功: {resolved}/{len(codes)} ({pct:.1f}%), 定制: {custom}')
    
    # 对每种skel抽1-2条展示
    samples_shown = 0
    for skel, count in skel_groups.head(30).items():
        subset = sd[sd['skel'] == skel]
        row = subset.iloc[0]
        spec = str(row['规格名'] or '')
        pid = str(row['商品id'] or '')
        
        # 找对应的编码
        match = gen[gen['平台商品id'].str.strip() == pid]
        if len(match) > 0:
            code = str(match.iloc[0]['商品编码'] or '').strip()
        else:
            code = '?未找到?'
        
        print(f'  [{count:>5d}条] {spec[:60]:60s} → {code}')
        samples_shown += 1
    
    if samples_shown < len(skel_groups):
        print(f'  ... 还有 {len(skel_groups) - samples_shown} 种格式未显示')
    
    print()
