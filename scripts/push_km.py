# -*- coding: utf-8 -*-
import os, shutil, subprocess

# 复制文件
src = r'D:\Desktop\平台和快麦原始商品\快麦商品.xlsx'
dst = r'D:\Desktop\sanyang-system\快麦商品.xlsx'
shutil.copy2(src, dst)
print(f'已复制: {os.path.getsize(dst)//1024}KB')

# git 提交
cmds = [
    'git add 快麦商品.xlsx',
    'git commit -m "add 快麦商品.xlsx (91MB 原始数据)"',
    'git push'
]

for cmd in cmds:
    print(f'> {cmd}')
    r = subprocess.run(cmd, shell=True, cwd=r'D:\Desktop\sanyang-system', capture_output=True, text=True)
    if r.stdout: print(r.stdout[:200])
    if r.stderr: print(r.stderr[:200])
    if r.returncode != 0:
        print(f'!!! 失败 rc={r.returncode}')
        break
