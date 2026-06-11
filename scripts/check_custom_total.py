# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

inpath = r'D:\Desktop\定制商品结构.txt'
with open(inpath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

total_count = 0  # 商品数
entry_count = 0  # 结构数

# 找所有 [xN] 并累加
for line in lines:
    m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
    if m:
        entry_count += 1
        total_count += int(m.group(1))

print(f'实际结构数: {entry_count}')
print(f'实际商品数: {total_count}')

# 更新文件头
new_lines = []
for line in lines:
    if line.startswith('结构数:'):
        new_lines.append(f'结构数: {entry_count}, 总商品数: {total_count}\n')
    else:
        new_lines.append(line)

with open(inpath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'✅ 已更新头部统计')

# 再统计其他文件总数对吗
# 原始总数 498090
other_files = [
    (r'D:\Desktop\扣底盒双插盒商品结构.txt', '扣底盒'),
    (r'D:\Desktop\纸箱商品结构.txt', '纸箱'),
    (r'D:\Desktop\剩余商品结构.txt', '剩余'),
]
other_total = 0
for fpath, name in other_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        m = re.search(r'共 (\d+) 条', f.read())
        if m:
            cnt = int(m.group(1))
            other_total += cnt
            print(f'{name}: {cnt} 条')

total_all = total_count + other_total
print(f'定制: {total_count} 条')
print(f'合计: {total_all} 条')
print(f'应等于: 498090')
if total_all == 498090:
    print('✅ 总数正确！')
else:
    print(f'❌ 差 {abs(total_all - 498090)} 条')
