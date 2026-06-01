# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import shutil

# 恢复无匹配备份
src = r'D:\Desktop\换绑输出\无匹配_待处理 - 副本.xlsx'
dst = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
shutil.copy2(src, dst)

# 删除第41批的OK文件（因为要重新跑）
okdir = r'D:\Desktop\换绑输出\OK文件'
f41 = os.path.join(okdir, '换绑文件_第41批.xlsx')
if os.path.exists(f41):
    os.remove(f41)
    print('已删除第41批')
print('已恢复无匹配备份，准备重新运行')
