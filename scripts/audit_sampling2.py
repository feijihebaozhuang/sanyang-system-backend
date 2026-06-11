# -*- coding: utf-8 -*-
"""逐个店铺深度抽样检查 - 显示每种规格的转换样例"""
import sys, re, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

SOURCE = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
OUTDIR = r'D:\Desktop'

def ms(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

print('读取源数据...')
df = pd.read_excel(SOURCE, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店', '商品id', '规格名', '规格id']
data['店'] = data['店'].str.strip()
data = data[data['店'] != '店铺名称']

SEP = '=' * 70

for shop_name in sorted(data['店'].unique()):
    safe = shop_name.replace('/', '_').replace('\\', '_').replace(':', '_')
    fp = os.path.join(OUTDIR, f'换绑_{safe}.xlsx')
    
    if not os.path.exists(fp):
        print(f'\n{SEP}')
        print(f'【{shop_name}】文件不存在!')
        continue
    
    try:
        gen = pd.read_excel(fp, dtype=str)
    except Exception as e:
        print(f'\n{SEP}')
        print(f'【{shop_name}】文件损坏: {e}')
        continue
    
    gen = gen.iloc[2:].copy()
    gen.columns = ['店铺名称', '平台商品id', '平台规格id', '商品编码']
    
    sd = data[data['店'] == shop_name].copy()
    total = len(sd)
    gen_total = len(gen)
    
    codes = gen['商品编码'].str.strip()
    custom = (codes == '定制链接').sum()
    resolved = gen_total - custom
    
    sd['skel'] = sd['规格名'].apply(ms)
    skel_groups = sd.groupby('skel').size().sort_values(ascending=False)
    
    print(f'\n{SEP}')
    print(f'[{shop_name}] 源{total}条 生成{gen_total}条 解析{resolved}({resolved/max(gen_total,1)*100:.1f}%) 定制{custom}({custom/max(gen_total,1)*100:.1f}%) {len(skel_groups)}种格式')
    print(SEP)
    
    # 对每种skel展示
    for idx, (skel, count) in enumerate(skel_groups.items()):
        if idx >= 30:
            print(f'  ... 还有 {len(skel_groups)-30} 种格式')
            break
        subset = sd[sd['skel'] == skel]
        spec = str(subset.iloc[0]['规格名'] or '')
        pid = str(subset.iloc[0]['商品id'] or '').strip()
        
        match = gen[gen['平台商品id'].str.strip() == pid]
        if len(match) > 0:
            code = str(match.iloc[0]['商品编码'] or '').strip()
        else:
            code = '?' + pid + '?'
        
        # 如果对应商品有多个规格，显示第一个
        row_codes = gen[gen['平台商品id'].str.strip() == pid]
        if len(row_codes) > 1:
            all_codes = '/'.join(row_codes['商品编码'].unique())
            if len(all_codes) < 40:
                code = all_codes
            else:
                code = str(row_codes.iloc[0]['商品编码'] or '')
        
        truncated = spec[:55] if len(spec) > 55 else spec
        print(f'  [{count:>5d}] {truncated} -> {code}')
    
    # 定制抽样
    if custom > 0:
        custom_rows = gen[codes == '定制链接']
        print(f'  定制抽样:')
        for i in range(min(3, len(custom_rows))):
            cr = custom_rows.iloc[i]
            pid2 = str(cr['平台商品id'] or '').strip()
            sid2 = str(cr['平台规格id'] or '').strip()
            match2 = sd[sd['商品id'].str.strip() == pid2]
            if len(match2) > 0:
                spec2 = str(match2.iloc[0]['规格名'] or '')
                tr = spec2[:60] if len(spec2) > 60 else spec2
                print(f'    {tr} -> 定制链接')
    
    # 内外径/材料统计
    resolved_df = gen[codes != '定制链接']
    dk_counts = {}
    mat_counts = {}
    for code in resolved_df['商品编码']:
        c = str(code).strip()
        if '-EB' in c or '-3B' in c:
            mat_counts['EB/纸箱'] = mat_counts.get('EB/纸箱', 0) + 1
        elif c.count('-') >= 2:
            parts = c.split('-')
            if len(parts) >= 3:
                dk_counts[parts[-2]] = dk_counts.get(parts[-2], 0) + 1
                mat_counts[parts[-1]] = mat_counts.get(parts[-1], 0) + 1
    
    if dk_counts:
        dk_str = ', '.join(f'{k}={v}' for k, v in sorted(dk_counts.items()))
        print(f'  内外径: {dk_str}')
    if mat_counts:
        mat_str = ', '.join(f'{k}={v}' for k, v in sorted(mat_counts.items()))
        print(f'  材料: {mat_str}')
    
    print()
