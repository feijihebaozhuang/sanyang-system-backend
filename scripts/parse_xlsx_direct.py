# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zipfile
import re

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'

with zipfile.ZipFile(source) as z:
    content = z.read('xl/worksheets/sheet1.xml').decode('utf-8', errors='replace')
    print(f'sheet1.xml 总长度: {len(content)} 字符')

# 逐行读取（用迭代器方式，不全部加载）
# 从 content 中逐行解析
print('逐行解析中...')
row_pattern = re.compile(r'<row[^>]*>(.*?)</row>', re.DOTALL)

count = 0
specs = []
for m in row_pattern.finditer(content):
    count += 1
    if count < 5:
        row_xml = m.group(1)
        # 提取 <is><t> 中的 inline 文本
        texts = re.findall(r'<t[^>]*>(.*?)</t>', row_xml)
        if count <= 2:
            print(f'行{count}: {texts[:10]}')
    if count == 3:
        # 取第一行数据的规格名称
        row_xml = m.group(1)
        texts = re.findall(r'<t[^>]*>(.*?)</t>', row_xml)
        if len(texts) > 5:
            specs.append(('第3行', texts[5]))  # 列5=规格名称
    if count == 498092:
        print(f'最后一行(第{count}行)')

print(f'总行数: {count}')
