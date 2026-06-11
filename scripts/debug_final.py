# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

s = '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个'

# 【的unicode是U+3010，】
# 试试用\uff3b \uff3d
# 或者直接硬编码

# 直接用汉字
print('直接汉字:', re.search(r'【', s))
# 用\u3010
print('用u3010:', re.search('\u3010', s))
# 用chr
print('用chr:', re.search(chr(0x3010), s))
# 用bytes
print('用bytes:', re.search(bytes([0xE3, 0x80, 0x90]), s.encode('utf-8')))
# 用[[]]
print('用[[]]:', re.search(r'\u3010', s))

# 到底是什么编码
b = s[5].encode('utf-8')
print(f'UTF-8 bytes: {b.hex()} = {b}')

# Python version
print(f'Python: {sys.version}')
