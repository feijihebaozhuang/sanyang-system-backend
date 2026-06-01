# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import shutil

src = r'D:\Desktop\换绑输出\无匹配_待处理 - 副本.xlsx'
dst = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
shutil.copy2(src, dst)
print(f'已从备份恢复无匹配_待处理')
