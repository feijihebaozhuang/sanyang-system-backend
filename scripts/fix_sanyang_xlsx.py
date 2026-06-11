# -*- coding: utf-8 -*-
"""强制替换三羊损坏的xlsx文件"""
import shutil, os, time

src = r'D:\Desktop\_sanyang_temp.xlsx'
dst = r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx'

print(f'源文件: {src} ({os.path.getsize(src)} bytes)')
print(f'目标文件: {dst} ({os.path.getsize(dst)} bytes)')

for attempt in range(5):
    try:
        if os.path.exists(dst):
            os.remove(dst)
            print(f'已删除旧文件 (attempt {attempt+1})')
            time.sleep(1)
        shutil.copy2(src, dst)
        print(f'已复制新文件 {os.path.getsize(dst)} bytes')
        break
    except PermissionError as e:
        print(f'权限错误: {e}, 重试中...')
        time.sleep(2)
else:
    print('多次重试后仍然失败')
    import sys
    sys.exit(1)

# 验证
import openpyxl
wb = openpyxl.load_workbook(dst)
rows = list(wb.iter_rows(values_only=True))
print(f'✅ 验证成功! 总行数: {len(rows)}')
print(f'第1行: {rows[0]}')
print(f'第2行: {rows[1]}')
print(f'最后1行: {rows[-1]}')
wb.close()
print('三羊文件修复完成')
