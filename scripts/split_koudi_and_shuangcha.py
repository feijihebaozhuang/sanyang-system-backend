# -*- coding: utf-8 -*-
"""
把 2-扣底盒双插盒商品结构.txt 拆成2个文件：
- 2-扣底盒商品结构.txt
- 3-双插盒商品结构.txt

后面的文件序号顺延：
- 原3-纸箱商品结构.txt → 4-纸箱商品结构.txt
- 原4-剩余商品结构.txt → 5-剩余商品结构.txt
- 原5-不属于定制的60个结构.txt → 6-不属于定制的60个结构.txt
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

f2_path = r'D:\Desktop\2-扣底盒双插盒商品结构.txt'
with open(f2_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# 解析条目
entries = []
current_start = None
current_section = []
current_shop = None

for i, line in enumerate(lines):
    # 文件开头
    if i < 3:
        continue
    if line.startswith('═══'):
        if current_start is not None:
            entries.append((current_start, i-1, current_shop, lines[current_start:i]))
        current_start = i
        # 提取店铺名
        m = re.match(r'═══ (.+?)（', line)
        current_shop = m.group(1) if m else '未知'
        continue

if current_start is not None:
    entries.append((current_start, len(lines)-1, current_shop, lines[current_start:]))

# 分类
koudi_entries = []
shuangcha_entries = []

for start, end, shop, entry_lines in entries:
    # 看结构是否含"双插"
    is_shuangcha = False
    for line in entry_lines:
        if '结构:' in line and '双插' in line:
            is_shuangcha = True
            break
    
    if is_shuangcha:
        shuangcha_entries.append(entry_lines)
    else:
        koudi_entries.append(entry_lines)

print(f'扣底盒: {len(koudi_entries)} 个店铺分组')
print(f'双插盒: {len(shuangcha_entries)} 个店铺分组')

# 统计
def count_items(entry_list):
    total_entries = 0
    total_count = 0
    for entry_lines in entry_list:
        for line in entry_lines:
            m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
            if m:
                total_entries += 1
                total_count += int(m.group(1))
    return total_entries, total_count

def write_file(entry_list, fpath, title):
    total_entries, total_count = count_items(entry_list)
    
    # 收集所有行
    all_lines = [f'{title}\n', f'结构数: {total_entries}, 总商品数: {total_count}\n\n']
    
    gidx = 0
    for entry_lines in entry_list:
        for line in entry_lines:
            if line.startswith('═══'):
                all_lines.append(line + '\n')
            elif re.match(r'\s*\[\d+\]', line):
                gidx += 1
                rest = re.sub(r'\[\d+\]', f'[{gidx}]', line, count=1)
                all_lines.append(rest + '\n')
            elif line.strip():
                all_lines.append(line + '\n')
            elif line == '':
                # 跳过空行
                pass
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(''.join(all_lines))
    print(f'  ✅ {fpath}: {total_entries} 结构, {total_count} 条')
    return total_entries, total_count

outdir = r'D:\Desktop'

# 写扣底盒和双插盒
k_e, k_c = write_file(koudi_entries, f'{outdir}\\2-扣底盒商品结构.txt', '扣底盒商品结构')
s_e, s_c = write_file(shuangcha_entries, f'{outdir}\\3-双插盒商品结构.txt', '双插盒商品结构')

# 重命名其他文件（4,5,6）
import shutil
shutil.copy(r'D:\Desktop\3-纸箱商品结构.txt', r'D:\Desktop\4-纸箱商品结构.txt')
shutil.copy(r'D:\Desktop\4-剩余商品结构.txt', r'D:\Desktop\5-剩余商品结构.txt')
shutil.copy(r'D:\Desktop\5-不属于定制的60个结构.txt', r'D:\Desktop\6-不属于定制的60个结构.txt')
print('  ✅ 4-纸箱商品结构.txt (复制)')
print('  ✅ 5-剩余商品结构.txt (复制)')
print('  ✅ 6-不属于定制的60个结构.txt (复制)')

# 验证总数
other_files = {
    '1-定制商品结构.txt': r'D:\Desktop\1-定制商品结构.txt',
    '4-纸箱商品结构.txt': r'D:\Desktop\4-纸箱商品结构.txt',
    '5-剩余商品结构.txt': r'D:\Desktop\5-剩余商品结构.txt',
    '6-不属于定制的60个结构.txt': r'D:\Desktop\6-不属于定制的60个结构.txt',
}
total_entries_all = k_e + s_e
total_counts_all = k_c + s_c
for name, fpath in other_files.items():
    with open(fpath, 'r', encoding='utf-8') as f:
        m = re.search(r'结构数: (\d+)', f.read())
        if m:
            total_entries_all += int(m.group(1))
print(f'\n6个文件合计: {total_entries_all} 结构 (应=1775)')
if total_entries_all == 1775:
    print('✅ 总数正确！')
else:
    print(f'❌ 差 {abs(total_entries_all - 1775)}')
