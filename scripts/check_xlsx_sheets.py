# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zipfile
import os

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print(f'文件大小: {os.path.getsize(source)} bytes')

# 直接看里面的sheet信息
with zipfile.ZipFile(source) as z:
    print(f'压缩包内文件: {z.namelist()[:20]}')
    # 读 workbook.xml 看 sheets
    if 'xl/workbook.xml' in z.namelist():
        content = z.read('xl/workbook.xml').decode('utf-8')
        import re
        sheets = re.findall(r'name="([^"]+)"', content)
        print(f'Sheets: {sheets}')
