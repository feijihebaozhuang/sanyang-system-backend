# -*- coding: utf-8 -*-
"""
从5-剩余商品结构.txt和6-不属于定制的60个结构.txt中，
删除应去定制的结构（黑&红、其他颜色等），
同时生成1a-定制商品结构（补充）.txt

1/2/3/4/4a 不动。
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def should_be_custom(sk):
    if '双面纯色' in sk:
        if '双面纯色【N个】黑色' in sk or '双面纯色【N个】白色' in sk:
            if '黑&红' not in sk:
                return False
        if '黑&红' in sk:
            return True
        for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '粉红色', '彩色']:
            if c in sk:
                return True
        return False
    for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '粉红色', '彩色']:
        if c in sk:
            return True
    if '黑&红' in sk:
        return True
    return False

# ===== 处理5-剩余商品结构.txt =====
f5_path = r'D:\Desktop\5-剩余商品结构.txt'
with open(f5_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 逐条目处理
all_entries = []
current_entry = []
for line in lines:
    if re.match(r'\s*\[\d+\]', line):
        if current_entry:
            all_entries.append(current_entry)
        current_entry = [line]
    elif current_entry:
        current_entry.append(line)
if current_entry:
    all_entries.append(current_entry)

# 分类
keep_entries = []
custom_entries = []
for entry_lines in all_entries:
    entry_text = ''.join(entry_lines)
    sk_match = re.search(r'结构:\s*(.+)', entry_text)
    if sk_match and should_be_custom(sk_match.group(1)):
        custom_entries.append(('5-剩余商品结构', entry_lines))
    else:
        keep_entries.append(entry_lines)

# 写回5（保留店铺标题）
with open(f5_path, 'w', encoding='utf-8') as f:
    # 保留文件头
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith('═══'):
            header_end = i
            break
    for i in range(header_end):
        f.write(lines[i])
    
    # 按店铺分组写入
    by_shop = {}
    for entry in keep_entries:
        shop_line = None
        for line in entry:
            if line.startswith('═══'):
                shop_line = line
                break
        if shop_line:
            shop_name = re.search(r'═══ (.+?)（', shop_line)
            shop_key = shop_name.group(1) if shop_name else '未知'
            by_shop.setdefault(shop_key, []).append(entry)
        else:
            by_shop.setdefault('未知', []).append(entry)
    
    gidx = 0
    for shop in sorted(by_shop.keys(), key=lambda s: -sum(sum(int(re.search(r'\[x(\d+)\]', l).group(1)) for l in e if re.search(r'\[x(\d+)\]', l)) for e in by_shop[s])):
        entries = by_shop[shop]
        shop_total = sum(int(re.search(r'\[x(\d+)\]', l).group(1)) for e in entries for l in e if re.search(r'\[x(\d+)\]', l))
        f.write(f'═══ {shop}（{len(entries)} 种格式, 共 {shop_total} 条）═══\n')
        for entry in entries:
            for line in entry:
                if re.match(r'\s*\[\d+\]', line):
                    gidx += 1
                    f.write(re.sub(r'\[\d+\]', f'[{gidx}]', line, count=1))
                elif not line.startswith('═══'):
                    f.write(line)
    
    # 更新文件头
# 重新统计
total_entries = 0
total_count = 0
with open(f5_path, 'r', encoding='utf-8') as f:
    for line in f:
        m = re.search(r'\[x(\d+)\]', line)
        if m and re.match(r'\s*\[\d+\]', line):
            total_entries += 1
            total_count += int(m.group(1))

# 更新文件头
with open(f5_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'结构数: \d+, 总商品数: \d+', f'结构数: {total_entries}, 总商品数: {total_count}', content)
with open(f5_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'5-剩余商品结构.txt 更新: {total_entries} 结构, {total_count} 条')

# ===== 生成1a文件 =====
outpath = r'D:\Desktop\1a-定制商品结构（补充）.txt'
total_structs = len(custom_entries)
total_count = 0

with open(outpath, 'w', encoding='utf-8') as f:
    f.write('定制商品结构（补充—从5和6中挑出）\n')
    f.write(f'结构数: {total_structs}, 总商品数: 待统计\n\n')
    gidx = 0
    for label, entry_lines in custom_entries:
        for line in entry_lines:
            m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:', line)
            if m:
                total_count += int(m.group(1))
                gidx += 1
                f.write(re.sub(r'\[\d+\]', f'[{gidx}]', line, count=1))
            elif not line.startswith('═══'):
                f.write(line)
        f.write('\n')

with open(outpath, 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'总商品数: 待统计', f'总商品数: {total_count}', content)
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'1a-定制商品结构（补充）.txt: {total_structs} 结构, {total_count} 条')

# ===== 验证总数 =====
files = [
    ('1-定制商品结构.txt', r'D:\Desktop\1-定制商品结构.txt'),
    ('1a-定制商品结构（补充）.txt', r'D:\Desktop\1a-定制商品结构（补充）.txt'),
    ('2-扣底盒商品结构.txt', r'D:\Desktop\2-扣底盒商品结构.txt'),
    ('3-双插盒商品结构.txt', r'D:\Desktop\3-双插盒商品结构.txt'),
    ('4-三层纸箱商品结构.txt', r'D:\Desktop\4-三层纸箱商品结构.txt'),
    ('4a-五层纸箱商品结构.txt', r'D:\Desktop\4a-五层纸箱商品结构.txt'),
    ('5-剩余商品结构.txt', r'D:\Desktop\5-剩余商品结构.txt'),
    ('6-不属于定制的60个结构.txt', r'D:\Desktop\6-不属于定制的60个结构.txt'),
]
total_s = 0
total_i = 0
for name, path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    m1 = re.search(r'结构数: (\d+)', content)
    m2 = re.search(r'总商品数: (\d+)', content)
    s = int(m1.group(1)) if m1 else 0
    i = int(m2.group(1)) if m2 else 0
    total_s += s
    total_i += i
    print(f'{name}: {s} 结构, {i} 条')

print(f'\n合计: {total_s} 结构, {total_i} 条 (应=1775结构, 498090条)')
if total_s == 1775 and total_i == 498090:
    print('✅ 完全正确！')
else:
    print(f'❌ 结构差 {abs(total_s-1775)}, 条数差 {abs(total_i-498090)}')
