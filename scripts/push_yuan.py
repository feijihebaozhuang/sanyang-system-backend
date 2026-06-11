# -*- coding: utf-8 -*-
import os, shutil, subprocess

# 复制原.xlsx
src = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
dst = r'D:\Desktop\sanyang-system\原.xlsx'
shutil.copy2(src, dst)
print(f'已复制: {os.path.getsize(dst)//1024}KB')

# 删除之前错误提交的快麦商品.xlsx，提交原.xlsx
cmds = [
    'git rm --cached 快麦商品.xlsx',
    'git add 原.xlsx',
    'git commit -m "fix: 替换为原.xlsx(正确文件), 移除快麦商品.xlsx(错误文件)"',
    'git push'
]

for cmd in cmds:
    print(f'> {cmd}')
    r = subprocess.run(cmd, shell=True, cwd=r'D:\Desktop\sanyang-system', capture_output=True, text=True)
    if r.stdout: print(r.stdout[:300])
    if r.stderr: print(r.stderr[:300])
    if r.returncode != 0:
        print(f'!!! 失败 rc={r.returncode}')
        break
