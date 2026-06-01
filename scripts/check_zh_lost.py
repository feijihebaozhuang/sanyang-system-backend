# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'
nm_path = os.path.join(OUT_DIR, '无匹配_待处理.xlsx')
pk_path = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

# 从原始平卡中提取止合数据（因为v3只是从无匹配删了，没改平卡）
# 但之前平卡已经显示0条止合了，所以止合数据原本应该在无匹配中
# 检查无匹配是否真的没有止合了
df_nm = pd.read_excel(nm_path)
mask = df_nm['店铺简称'].str.contains('止合', na=False)
zh_in_nm = df_nm[mask]
print(f'无匹配中止合: {len(zh_in_nm)} 条')

# 再看平卡
df_pk = pd.read_excel(pk_path)
mask_pk = df_pk['店铺简称'].str.contains('止合', na=False)
zh_in_pk = df_pk[mask_pk]
print(f'平卡中止合: {len(zh_in_pk)} 条')

if len(zh_in_nm) == 0 and len(zh_in_pk) == 0:
    print('\n止合数据已全部从无匹配和平卡中移除！')
    print('但v3只匹配了13条，剩余的1106条丢失了。')
    print('\n需要从git或备份恢复原始文件。')
