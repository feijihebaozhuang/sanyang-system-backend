# -*- coding: utf-8 -*-
"""搜索所有定制相关文件"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 搜桌面
desktop = r'd:\Desktop'
all_files = []
for root, dirs, files in os.walk(desktop):
    for f in files:
        if '定制' in f and f.endswith('.xlsx'):
            fp = os.path.join(root, f)
            sz = os.path.getsize(fp)
            all_files.append((fp, sz))

print(f'找到{len(all_files)}个定制文件:')
for fp, sz in sorted(all_files):
    print(f'  {fp} ({sz/1024:.1f}KB)')

# 也搜换绑输出
out = r'd:\Desktop\换绑输出'
if os.path.exists(out):
    print(f'\n换绑输出目录:')
    for f in sorted(os.listdir(out)):
        if f.endswith('.xlsx'):
            fp = os.path.join(out, f)
            sz = os.path.getsize(fp)
            print(f'  {f} ({sz/1024:.1f}KB)')
