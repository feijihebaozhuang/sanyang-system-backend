# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '双面纯色【50个】黑色;【长度 13 厘米】【宽度 10 厘米】系列 外径 130x100x20 mm'
print(f'规格: {s}')
print()

# A1: 宽【W】高【H】... 长【L】
m = re.search(r'宽【\s*([\d.]+)\s*cm?\s*】.*?高【\s*([\d.]+)\s*cm?\s*】.*?长【\s*([\d.]+)\s*cm?\s*】', s)
print(f'A1宽高+长: {m}')

# A2: 长【L】宽【W】高【H】
m = re.search(r'长【\s*([\d.]+)\s*cm?\s*】.*?宽【\s*([\d.]+)\s*cm?\s*】.*?高【\s*([\d.]+)\s*cm?\s*】', s)
print(f'A2长宽高: {m}')

# A3: 飞机盒【长度L】
m = re.search(r'飞机盒【长度\s*([\d.]+)\s*CM?\s*】.*?【宽度\s*([\d.]+)\s*CM?\s*】\s*X\s*【高度\s*([\d.]+)\s*CM?\s*】', s)
print(f'A3飞机盒: {m}')

# A4: 外径
m = re.search(r'外径[：:]*\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)', s)
print(f'A4外径: {m}')
if m:
    print(f'  提取: {m.group(1)}, {m.group(2)}, {m.group(3)}')

# B1: 【LxWxH】
m = re.search(r'【\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*】', s)
print(f'B1【LxWxH】: {m}')

# B2: 长LxWxH
m = re.search(r'[长L]+\s*[：:]?\s*(\d+\.?\d*)\s*(?:cm|mm)?\s*[xX*]\s*(\d+\.?\d*)\s*(?:cm|mm)?\s*[xX*]\s*(\d+\.?\d*)', s)
print(f'B2长前缀LxWxH: {m}')

# B3: ;LxWxH在末尾
m = re.search(r'(?:[；;]\s*|^)(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*$', s)
print(f'B3;LxWxH末尾: {m}')

# B4: 裸LxWxH
m = re.search(r'(?:^|[\s；;])(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)', s)
print(f'B4裸LxWxH: {m}')

# 现在手动检查"长度 13 厘米"——这个是不是被任何格式匹配了
m_len = re.search(r'【长度\s*([\d.]+)\s*厘米', s)
print(f'\n【长度{cm}】: {m_len}')
if m_len:
    print(f'  数值: {m_len.group(1)}')

m_wid = re.search(r'【宽度\s*([\d.]+)\s*厘米', s)
print(f'【宽度{cm}】: {m_wid}')
if m_wid:
    print(f'  数值: {m_wid.group(1)}')
