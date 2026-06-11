# -*- coding: utf-8 -*-
"""
对比：原始df中哪些被之前的"宽松规则"判为定制，
但现在的严格规则没判为定制的
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)

# 宽松规则（之前的 is_custom）
def is_custom_loose(s):
    keywords = ['定制', '订制', '定做', '加工定制', '不接受退货',
                '咨询客服', '拍下联系客服', '定制产品', '定制拍单',
                '定制尺寸', '万款现货', '联系客服备注', '详情咨询',
                '更多尺寸', '下拉查看', '下拉-', '1000款现模',
                '更多尺寸看详情', '详情-现模', '1000个尺寸']
    for kw in keywords:
        if kw in s: return True
    if '珍珠棉' in s: return True
    nums = re.findall(r'[\d.]+', s)
    has_dim = bool(re.search(r'[\d.]+\s*[xX*×]\s*[\d.]+', s)) or bool(re.search(r'【\s*[\d.]+', s))
    if len(nums) < 3 and not has_dim:
        if '飞机盒' in s or '纸箱' in s or '扣底盒' in s or '信封' in s:
            return False
        if len(re.sub(r'[\s【】；;，,、\-/（）()（）【】]', '', s)) < 20:
            return False
        return True
    return False

# 严格规则（现在的 is_custom）
def is_custom_strict(s):
    if re.search(r'[\d.]+\s*[xX*×]\s*[\d.]+\s*[xX*×]\s*[\d.]+', s): return False
    if re.search(r'【\s*[\d.]+', s): return False
    if re.search(r'[长宽高][度]*\s*[：:]?\s*【\s*[\d.]+', s): return False
    for kw in ['定制','订制','定做','加工定制','不接受退货','咨询客服','拍下联系客服',
               '定制产品','定制拍单','定制尺寸','万款现货','联系客服备注','详情咨询',
               '更多尺寸','下拉查看','1000款现模','更多尺寸看详情','详情-现模']:
        if kw in s: return True
    if '珍珠棉' in s: return True
    if len(re.findall(r'[\d.]+', s)) == 0: return True
    return False

# 看看宽松=定制 但 严格≠定制 的有多少
diff_loose_strict = []
for _, row in df.iterrows():
    s = str(row.get('平台规格名称', '')).strip()
    if not s: continue
    loose = is_custom_loose(s)
    strict = is_custom_strict(s)
    if loose and not strict:
        diff_loose_strict.append((s[:80]))

print(f'宽松规则判定制但严格规则未判: {len(diff_loose_strict)} 条')
print('\n前30条:')
for s in diff_loose_strict[:30]:
    print(f'  {s}')

# 看看现在的256条定制是什么
print(f'\n\n现在的定制链接内容:')
custom_file = r'D:\Desktop\定制链接商品.xlsx'
df_c = pd.read_excel(custom_file, skiprows=1, dtype=str)
for _, r in df_c.iterrows():
    print(f'  {r["规格名称"][:70]}')
