# -*- coding: utf-8 -*-
"""
从5-剩余商品结构.txt和6-不属于定制的60个结构.txt中，
挑出应该去定制的结构，生成 1a-定制商品结构（补充）.txt
不修改任何原有文件。

定制条件：
1. 含"双面纯色"且不是白色/黑色 → 定制（黑&红、蓝色、红色等）
2. 含其他明确颜色关键词 → 定制
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def should_be_custom(sk):
    """检查是否应该去定制"""
    # 双面纯色：只有黑&红或其他颜色时算定制
    if '双面纯色' in sk:
        # 如果是纯黑或纯白 → 不算定制
        if '双面纯色【N个】黑色' in sk or '双面纯色【N个】白色' in sk:
            if '黑&红' not in sk:
                return False
        # 黑&红 → 定制
        if '黑&红' in sk:
            return True
        # 其他颜色
        for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '粉红色', '彩色']:
            if c in sk:
                return True
        return False
    
    # 非双面纯色：直接看颜色关键词
    for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '粉红色', '彩色']:
        if c in sk:
            return True
    if '黑&红' in sk:
        return True
    
    return False

all_entries = []

for fname, label in [
    (r'D:\Desktop\5-剩余商品结构.txt', '5-剩余商品结构'),
    (r'D:\Desktop\6-不属于定制的60个结构.txt', '6-不属于定制的60个结构'),
]:
    with open(fname, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_entry = []
    for line in lines:
        if re.match(r'\s*\[\d+\]', line):
            if current_entry:
                all_entries.append((label, current_entry))
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)
    if current_entry:
        all_entries.append((label, current_entry))

custom_entries = []
for label, entry_lines in all_entries:
    entry_text = ''.join(entry_lines)
    sk_match = re.search(r'结构:\s*(.+)', entry_text)
    if sk_match and should_be_custom(sk_match.group(1)):
        custom_entries.append((label, entry_lines))

print(f'找到 {len(custom_entries)} 个应去定制的条目')
for label, entry_lines in custom_entries:
    for line in entry_lines:
        if re.match(r'\s*\[\d+\]', line):
            print(f'  {line.strip()[:80]}')
            break

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
            else:
                f.write(line)
        f.write('\n')

with open(outpath, 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'总商品数: 待统计', f'总商品数: {total_count}', content)
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n✅ {outpath}: {total_structs} 结构, {total_count} 条')
print('原文件未被修改。')
