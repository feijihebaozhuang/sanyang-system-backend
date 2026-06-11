# -*- coding: utf-8 -*-
import re

s = '宽【10cm】高【9cm】;【100个】长【40cm】'

m = re.search(r'宽[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]'
              r'.*?'
              r'高[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]'
              r'.*?'
              r'(?:长度?)[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]', s)
print(f'A1: {m}')
if m:
    print(f'  L={m.group(5)}({m.group(6)!r}) W={m.group(1)}({m.group(2)!r}) H={m.group(3)}({m.group(4)!r})')

# 定制里的新格式
s2 = '宽 10 高 10 cm;长度 11 cm【100个】白色'
m2 = re.search(r'宽[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?'
               r'.*?'
               r'高[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?'
               r'.*?'
               r'(?:长度?)[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?', s2)
print(f'\nA1 on s2: {m2}')
if m2:
    print(f'  L={m2.group(5)}({m2.group(6)!r}) W={m2.group(1)}({m2.group(2)!r}) H={m2.group(3)}({m2.group(4)!r})')
else:
    # 是 【】\[]? 的问题
    m_w = re.search(r'宽[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?', s2)
    print(f'  宽部分: {m_w}')
    m_h = re.search(r'高[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?', s2)
    print(f'  高部分: {m_h}')
    m_l = re.search(r'长度?[【\[]?\s*([\d.]+)\s*(\w*)\s*[】\]]?', s2)
    print(f'  长部分: {m_l}')

# s3: 定制里的嵌套括号
s3 = '宽【10cm】高【2cm】【内径】;【100个】长度【11cm【内径】】'
m3 = re.search(r'宽[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]'
               r'.*?'
               r'高[【\[]\s*([\d.]+)\s*(\w*)[^】]*[】\]]'
               r'.*?'
               r'(?:长度?)[【\[]\s*([\d.]+)\s*(\w*)\s*[】\]]', s3)
print(f'\nA1 on s3: {m3}')
if m3:
    print(f'  L={m3.group(5)} W={m3.group(1)} H={m3.group(3)}')
