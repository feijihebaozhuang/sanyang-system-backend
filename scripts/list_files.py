# -*- coding: utf-8 -*-
"""列出目录下所有文件的原始字节"""
import os
out = r'd:\Desktop\换绑输出'
for f in os.listdir(out):
    # 输出原始字节便于排查编码问题
    raw = f.encode('utf-8', errors='replace')
    print(f'  len={len(f)} chars={repr(f)}')
