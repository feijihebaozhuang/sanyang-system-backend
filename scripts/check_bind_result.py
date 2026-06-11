# -*- coding: utf-8 -*-
"""检查之前的匹配结果是否正确"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd

# 读平台商品
print("读取平台商品...", flush=True)
df = pd.read_excel(r'd:\Desktop\平台商品.xlsx', sheet_name='报表1', header=2, dtype=str)
print(f"总 {len(df)} 行", flush=True)

# 读换绑文件
print("读取换绑结果...", flush=True)
bind = pd.read_excel(r'd:\Desktop\换绑输出\换绑文件.xlsx', sheet_name='Sheet1', header=1, dtype=str)
print(f"换绑 {len(bind)} 条", flush=True)

# 检查前1000条匹配有没有明显的内外径错误
# 建一个平台规格名 → 快麦编码的映射
bind_map = {}
for _, row in bind.iterrows():
    pid = str(row['平台商品id'] or '').strip()
    code = str(row['商品编码'] or '').strip()
    if pid and code:
        bind_map[pid] = code

# 抽样检查：看那些匹配到内径编码的，平台规格名是否写了内径
print("\n=== 抽样检查前200条匹配到内径编码的 ===", flush=True)
checked = 0
errors = 0
for _, row in bind.head(500).iterrows():
    pid = str(row['平台商品id'] or '').strip()
    code = str(row['商品编码'] or '').strip()
    if not pid or not code:
        continue
    # 找平台规格名
    spec_rows = df[df.iloc[:, 1].astype(str).str.strip() == pid]
    if len(spec_rows) == 0:
        continue
    spec_name = str(spec_rows.iloc[0, 2] or '')
    
    is_inner_code = '内径' in code
    spec_says_outer = '外径' in spec_name
    spec_says_inner = '内径' in spec_name
    
    if is_inner_code and spec_says_outer and not spec_says_inner:
        errors += 1
        if checked < 20:
            print(f"  可能错误: 规格名[{spec_name[:80]}] → 内径编码[{code}]", flush=True)
            checked += 1

print(f"\n前500条中: 外径规格匹配到内径编码的 {errors} 条", flush=True)
print(f"这可能是正确的（外径转内径匹配），需要进一步验证", flush=True)
