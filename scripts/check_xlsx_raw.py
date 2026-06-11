# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zipfile
import re
from lxml import etree

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'

with zipfile.ZipFile(source) as z:
    # 看看 sheet1.xml 的大小
    info = z.getinfo('xl/worksheets/sheet1.xml')
    print(f'sheet1.xml 大小: {info.file_size} bytes')
    
    # 读共享字符串
    if 'xl/sharedStrings.xml' in z.namelist():
        info2 = z.getinfo('xl/sharedStrings.xml')
        print(f'sharedStrings.xml 大小: {info2.file_size} bytes')
    
    # 读sheet内容前几行xml
    content = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    # 提取 row 元素
    rows = re.findall(r'<row[^>]*>(.*?)</row>', content, re.DOTALL)
    print(f'row 元素数: {len(rows)}')
    
    # 看前几个row
    for i, row_xml in enumerate(rows[:5]):
        cells = re.findall(r'<c[^>]*>(.*?)</c>', row_xml, re.DOTALL)
        cell_data = []
        for c in cells:
            r_ref = re.search(r'<c r="([^"]+)"', c)
            v = re.search(r'<v>(.*?)</v>', c)
            t = re.search(r' t="([^"]+)"', c)
            cell_data.append(f'{r_ref.group(1) if r_ref else "?"}={v.group(1) if v else "?"}(t={t.group(1) if t else "inline"})')
        print(f'  行{i}: {cell_data[:10]}')
