import pandas as pd, re
from gen_ys_bind import CONFIG, make_skel, p_五层特硬, universal_fallback

df = pd.read_excel(r'D:\Desktop\未识别飞机盒_待分析.xlsx', dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
sd = data[data['店铺名称'].str.strip() == '深圳市友尚包装有限公司']

# Test EB items
target = '长宽N*N；【五层特硬】N个装；高Ncm;长宽N*N;【五层特硬】N个装;高Ncm'
print(f'Target in CONFIG: {target in CONFIG}')
if target in CONFIG:
    print(f'  dk={CONFIG[target][0]}, mat={CONFIG[target][1]}')

for i, row in sd.iterrows():
    spec = str(row['平台规格名称'] or '').strip()
    sk = make_skel(spec)
    if '五层' in spec:
        print(f'SPEC: {spec}')
        print(f'SK: [{sk}]')
        print(f'MATCH: {sk in CONFIG}')
        if sk in CONFIG:
            cfg = CONFIG[sk]
            print(f'  cfg={cfg}')
            try:
                dims = cfg[2](spec)
                print(f'  dims={dims}')
            except Exception as e:
                print(f'  error: {e}')
        else:
            fb = universal_fallback(spec)
            print(f'  fallback={fb}')
        print()
        if i > 10: break
