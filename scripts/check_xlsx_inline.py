# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zipfile
import re

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'

with zipfile.ZipFile(source) as z:
    content = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    
    # 用迭代器读，不要一次性处理 892MB
    # 提取前5 row 的 cell 值和 is（单元格内容在 <is> 里，因为是 inline）
    rows = re.findall(r'<row[^>]*>(.*?)</row>', content, re.DOTALL)
    print(f'总行数: {len(rows)}')
    
    for i, row_xml in enumerate(rows[:4]):
        # 提取 <is><t>内容</t></is> 里的 inline 文本
        texts = re.findall(r'<is>(?:<r>)?<t[^>]*>(.*?)</t>(?:</r>)?</is>', row_xml, re.DOTALL)
        print(f'行{i}: {texts[:10]}')
