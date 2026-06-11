# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

files = ['换绑文件_第1批.xlsx','换绑文件_第2批.xlsx','换绑文件_第3批.xlsx','换绑文件_第4批.xlsx',
         '定制类_换绑文件.xlsx','定制类_换绑文件_第2批.xlsx','定制类_换绑文件_第3批.xlsx',
         '定制类_换绑文件_第4批.xlsx']

for fn in files:
    fp = os.path.join(out, fn)
    if not os.path.exists(fp):
        print(f"{fn}: 不存在")
        continue
    wb = oxl.load_workbook(fp, data_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(min_row=3, values_only=True))
    wb.close()
    
    ali_shops = set()
    for r in rows:
        if not r or not r[0]: continue
        name = str(r[0]).strip()
        if '阿里' in name or '深圳' in name or '东莞' in name:
            ali_shops.add(name)
    
    print(f"{fn}: 阿里相关店铺名称 = {ali_shops}")
