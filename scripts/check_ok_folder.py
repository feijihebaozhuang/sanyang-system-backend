# -*- coding: utf-8 -*-
"""查看OK文件夹所有内容"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ok_dir = r'd:\Desktop\换绑输出\OK文件'
if not os.path.exists(ok_dir):
    print('OK文件夹不存在')
    sys.exit(0)

print('OK文件夹内容:')
for f in sorted(os.listdir(ok_dir)):
    fp = os.path.join(ok_dir, f)
    sz = os.path.getsize(fp)
    print(f'  {f} ({sz/1024:.1f}KB)')
