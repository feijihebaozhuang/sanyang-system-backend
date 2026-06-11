# -*- coding: utf-8 -*-
"""
把 4-纸箱商品结构.txt 拆成2个文件：
- 4-三层纸箱商品结构.txt  (含"三层")
- 4a-五层纸箱商品结构.txt (含"五层"、N层但是没有"三层"的算五层)
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===== 解析条目 =====
fpath = r'D:\Desktop\4-纸箱商品结构.txt'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# 解析每个条目
entries = []
current_shop = None
current_lines = []
in_entry = False

for line in lines:
    if line.startswith('═══'):
        if in_entry and current_shop:
            entries.append((current_shop, current_lines))
        current_shop = None
        current_lines = [line]
        in_entry = True
        m = re.match(r'═══ (.+?)（', line)
        if m:
            current_shop = m.group(1)
        continue
    
    if in_entry and current_shop:
        if re.match(r'\s*\[\d+\]', line):
            # 新条目，先保存旧的
            if any(re.match(r'\s*\[\d+\]', l) for l in current_lines[1:]):
                pass
            current_lines.append(line)
        elif line.strip().startswith('样例:') or line.strip().startswith('pid=') or line.strip() == '':
            current_lines.append(line)
        else:
            current_lines.append(line)

if in_entry and current_shop:
    entries.append((current_shop, current_lines))

print(f'共 {len(entries)} 个店铺分组')

# 把每个店铺分组里的条目拆成三层/五层
san_entries = []
wu_entries = []

for shop, entry_lines in entries:
    san_items = []
    wu_items = []
    current_item = []
    for line in entry_lines:
        if re.match(r'\s*\[\d+\]', line):
            if current_item:
                # 判断属于三层还是五层
                item_text = '\n'.join(current_item)
                if '三层' in item_text:
                    san_items.append(current_item[:])
                else:
                    wu_items.append(current_item[:])
                current_item = []
        current_item.append(line)
    
    if current_item:
        item_text = '\n'.join(current_item)
        if '三层' in item_text:
            san_items.append(current_item[:])
        else:
            wu_items.append(current_item[:])
    
    if san_items:
        san_entries.append((shop, san_items))
    if wu_items:
        wu_entries.append((shop, wu_items))

# 统计
def count_items(entry_list):
    total_entries = 0
    total_count = 0
    for shop, items in entry_list:
        for item_lines in items:
            for line in item_lines:
                m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
                if m:
                    total_entries += 1
                    total_count += int(m.group(1))
    return total_entries, total_count

def write_file(entry_list, fpath, title):
    total_entries, total_count = count_items(entry_list)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f'{title}\n')
        f.write(f'结构数: {total_entries}, 总商品数: {total_count}\n\n')
        gidx = 0
        for shop, items in entry_list:
            shop_total = sum(
                int(re.search(r'\[x(\d+)\]', line).group(1))
                for item in items for line in item if re.search(r'\[x(\d+)\]', line)
            )
            n_items = len(items)
            f.write(f'═══ {shop}（{n_items} 种格式, 共 {shop_total} 条）═══\n')
            for item_lines in items:
                for line in item_lines:
                    if re.match(r'\s*\[\d+\]', line):
                        gidx += 1
                        rest = re.sub(r'\[\d+\]', f'[{gidx}]', line, count=1)
                        f.write(f'{rest}\n')
                    elif line.strip():
                        f.write(f'{line}\n')
                f.write('\n')
    
    print(f'  ✅ {fpath}: {total_entries} 结构, {total_count} 条')

outdir = r'D:\Desktop'
write_file(san_entries, f'{outdir}\\4-三层纸箱商品结构.txt', '三层纸箱商品结构')
write_file(wu_entries, f'{outdir}\\4a-五层纸箱商品结构.txt', '五层纸箱商品结构')

# 验证
s_e, s_c = count_items(san_entries)
w_e, w_c = count_items(wu_entries)
print(f'\n三层: {s_e} 结构, {s_c} 条')
print(f'五层: {w_e} 结构, {w_c} 条')
print(f'合计: {s_e + w_e} 结构, {s_c + w_c} 条 (应=40结构, 36197条)')
if s_e + w_e == 40 and s_c + w_c == 36197:
    print('✅ 总数正确！')
else:
    print('❌ 不对')
