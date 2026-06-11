# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl

pid = '807069131375'
wb = openpyxl.load_workbook(r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx')
ws = wb.active
for row in ws.iter_rows(min_row=3, values_only=True):
    pid_x = str(row[1] or '')
    if pid_x == pid:
        print(f'{row[3]}')
wb.close()
