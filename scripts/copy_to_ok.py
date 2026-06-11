# -*- coding: utf-8 -*-
"""将换绑输出第8-14批拷贝到OK文件目录，重命名为33-39"""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

srcdir = r'D:\Desktop\换绑输出'
dstdir = r'D:\Desktop\换绑输出\OK文件'

# 复制的映射: 源批号 -> 目标批号
mapping = {
    8: 33, 9: 34, 10: 35, 11: 36,
    12: 37, 13: 38, 14: 39
}

for src_batch, dst_batch in mapping.items():
    # 主文件
    src = os.path.join(srcdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{src_batch}\u6279.xlsx')
    dst = os.path.join(dstdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{dst_batch}\u6279.xlsx')
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'\u5df2\u590d\u5236: \u7b2c{src_batch}\u6279 -> \u7b2c{dst_batch}\u6279')
    else:
        print(f'\u4e0d\u5b58\u5728: \u7b2c{src_batch}\u6279')
    
    # 拆分部分
    parts = [f for f in os.listdir(srcdir) if f.startswith(f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{src_batch}\u6279_')]
    for p in sorted(parts):
        srcp = os.path.join(srcdir, p)
        dstp = os.path.join(dstdir, p.replace(f'\u7b2c{src_batch}\u6279_', f'\u7b2c{dst_batch}\u6279_'))
        shutil.copy2(srcp, dstp)
        print(f'  \u62c6\u5206: {p} -> {os.path.basename(dstp)}')

print(f'\n\u5b8c\u6210! \u7b2c8-14\u6279\u5df2\u4f5c\u4e3a\u7b2c{list(mapping.values())[0]}-{list(mapping.values())[-1]}\u6279\u52a0\u5165OK\u6587\u4ef6')
