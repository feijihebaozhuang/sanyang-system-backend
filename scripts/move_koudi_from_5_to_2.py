# -*- coding: utf-8 -*-
"""
从 5-不属于定制的60个结构.txt 中删掉3个扣底盒结构的条目，
把这3个加到 2-扣底盒双插盒商品结构.txt 中。
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REMOVE_PIDS = {'5419370666499', '4886612768367', '4891354397901'}

# ===== 从5号文件删除 =====
f5_path = r'D:\Desktop\5-不属于定制的60个结构.txt'
with open(f5_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# 找到要删除的条目范围
entries = []
current_start = None
for i, line in enumerate(lines):
    if re.match(r'\[\d+\]', line):
        if current_start is not None:
            entries.append((current_start, i-1))
        current_start = i

if current_start is not None:
    entries.append((current_start, len(lines)-1))

# 找要删除的条目索引
pid_to_entry_idx = {}
for idx, (start, end) in enumerate(entries):
    for j in range(start, end+1):
        m = re.match(r'\s*pid=(.+)', lines[j])
        if m and m.group(1).strip() in REMOVE_PIDS:
            pid_to_entry_idx[m.group(1).strip()] = idx

print(f'5号中匹配到的条目: {len(pid_to_entry_idx)}')

# 保存要移动的条目内容
moved_entries = []
for pid, idx in pid_to_entry_idx.items():
    start, end = entries[idx]
    moved_entries.append('\n'.join(lines[start:end+1]))
    # 标记删除
    for j in range(start, end+1):
        lines[j] = None

# 重写5号
new_lines = []
prev_none = False
for line in lines:
    if line is None:
        prev_none = True
        continue
    if prev_none and (line == '' or line == '\r'):
        prev_none = False
        continue
    prev_none = False
    new_lines.append(line)

# 更新头部统计
total_entries = 0
total_count = 0
for line in new_lines:
    m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
    if m:
        total_entries += 1
        total_count += int(m.group(1))

final_lines = []
for line in new_lines:
    if line.startswith('结构数:'):
        final_lines.append(f'结构数: {total_entries}, 总商品数: {total_count}\n')
    else:
        final_lines.append(line)

with open(f5_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_lines))
print(f'✅ 5号文件更新: {total_entries} 结构, {total_count} 条')

# ===== 加到2号扣底盒文件 =====
f2_path = r'D:\Desktop\2-扣底盒双插盒商品结构.txt'
with open(f2_path, 'r', encoding='utf-8') as f:
    f2_content = f.read()

f2_lines = f2_content.split('\n')

# 找到第一个店铺标题的位置（除了文件头）
first_shop_idx = None
for i, line in enumerate(f2_lines):
    if line.startswith('═══'):
        first_shop_idx = i
        break

if first_shop_idx:
    # 在文件头后面插入新增条目
    insert_pos = first_shop_idx
else:
    insert_pos = len(f2_lines)

# 插入空行 + 店铺标题 + 条目
new_f2_lines = f2_lines[:insert_pos]

# 新增的3个条目各自带店铺标题
for entry_text in moved_entries:
    # 解析出店铺名
    shop_name = None
    for line in entry_text.split('\n'):
        m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:\s*(.+)', line)
        if m:
            # 判断是哪个店铺
            skeleton = m.group(2)
            if '扣底盒' in skeleton or '扣底纸盒' in skeleton:
                if '黄色' in skeleton:
                    shop_name = '天猫扣底盒'
                else:
                    shop_name = '天猫彩色'
            break
    
    if not shop_name:
        shop_name = '天猫扣底盒'
    
    # 该条目已按原样加入到2号文件
    new_f2_lines.append(f'═══ {shop_name}（1 种格式, 共 1 条）═══')
    new_f2_lines.append(entry_text)
    new_f2_lines.append('')

# 跳过文件头之后的原有内容，保留原有店铺结构和条目
# 把原来的店铺标题和条目都加回去
seen_shop_sections = set()
for i, line in enumerate(f2_lines):
    if i < insert_pos:
        continue
    new_f2_lines.append(line)

# 更新2号文件头部统计
total_entries2 = 0
total_count2 = 0
for line in new_f2_lines:
    m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
    if m:
        total_entries2 += 1
        total_count2 += int(m.group(1))

final_f2_lines = []
for line in new_f2_lines:
    if line.startswith('结构数:'):
        final_f2_lines.append(f'结构数: {total_entries2}, 总商品数: {total_count2}\n')
    else:
        final_f2_lines.append(line)

with open(f2_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_f2_lines))
print(f'✅ 2号文件更新: {total_entries2} 结构, {total_count2} 条')

# 验证
print(f'\n5+2条数检查:')
print(f'  5号: {total_entries} 结构')
print(f'  2号: {total_entries2} 结构')
print(f'  5+2合计: {total_entries + total_entries2} 结构')
# 原来 60-12 = 48 + 12+3 = 15 
print(f'  原始5号: 60 + 原始2号: 12 = 72')
print(f'  现在5号: {total_entries} + 现在2号: {total_entries2} = {total_entries + total_entries2}')
