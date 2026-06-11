# -*- coding: utf-8 -*-
"""
从定制商品结构.txt 中删除指定pid的结构条目。
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REMOVE_PIDS = set()

pid_text = """pid=4825115257961
pid=4825115257960
pid=5024084823689
pid=5024084823688
pid=5024084823687
pid=5024084823686
pid=4699812631698
pid=4699812631725
pid=4699812631724
pid=4514045260014
pid=4690595315980
pid=4514045260013
pid=4690595315979
pid=4529804717531
pid=4529804717532
pid=4702033979698
pid=4702033979699
pid=4693016566643
pid=4693016566611
pid=4693016566642
pid=4348482717568
pid=4524120400254
pid=4524120400305
pid=4349450997375
pid=4524120400304
pid=4524120400283
pid=4524120400255
pid=4524120400282
pid=4514045260012
pid=4690595315978
pid=4514045260011
pid=4693016566677
pid=4693016566629
pid=4693016566676
pid=4693016566628
pid=4839120956836
pid=4839120956835
pid=4525336968135
pid=4517217318406
pid=4525336968134
pid=4517217318403
pid=4699812631709
pid=4699812631747
pid=4699812631746
pid=4516538470072
pid=4345810332432
pid=4345810332435
pid=4699161887763
pid=4699161887723
pid=4699161887762
pid=5419370666499
pid=4886612768367
pid=4891354397901
pid=5c0938bee1f58a3d7c6c2f8ad15ff1f7715544087901
pid=2ec84270395f70df2c674d2c665192a8716008877627
pid=8338da557634da644fe12ba82bba9236715544087901
pid=21c275a6dc6cde70cb1fcca18f733c79715544087901
pid=82ede24fa38c61f5a05866ef3615ec22715544087901
pid=f392d34877d668161374edf72883e8d8716008877627
pid=a780625eeaaf41b49ec8bb047f49ef2b721836684147"""

for line in pid_text.strip().split('\n'):
    pid = line.strip().replace('pid=', '')
    if pid:
        REMOVE_PIDS.add(pid)

print(f'需要删除的 pid 数量: {len(REMOVE_PIDS)}')

inpath = r'D:\Desktop\定制商品结构.txt'
with open(inpath, 'r', encoding='utf-8') as f:
    content = f.read()

# 按条目解析
# 每个条目由序号行开头（[N]），后跟结构行、样例行、pid行、空行
# 保留文件头（前3行）

lines = content.split('\n')

# 找到第一个条目序号行的位置
entries = []
current_entry_start = None

for i, line in enumerate(lines):
    if re.match(r'\[\d+\]', line):
        if current_entry_start is not None:
            # 保存上一个条目
            entries.append((current_entry_start, i-1))
        current_entry_start = i
    elif line.strip().startswith('═══') and current_entry_start is not None:
        # 新店铺标题，先保存前一条目
        entries.append((current_entry_start, i-1))
        current_entry_start = None

# 最后一个条目
if current_entry_start is not None:
    entries.append((current_entry_start, len(lines)-1))

print(f'共 {len(entries)} 个条目')

# 建立 pid -> 条目索引的映射
pid_to_entry = {}
for idx, (start, end) in enumerate(entries):
    for j in range(start, end+1):
        m = re.match(r'\s*pid=(.+)', lines[j])
        if m:
            pid = m.group(1).strip()
            if pid in REMOVE_PIDS:
                pid_to_entry[pid] = idx
            break

print(f'匹配到的条目: {len(pid_to_entry)}')
if len(pid_to_entry) != len(REMOVE_PIDS):
    missing = REMOVE_PIDS - set(pid_to_entry.keys())
    print(f'未找到的pid: {missing}')

# 删除匹配的条目（从后往前删，保持索引不变）
entry_indices_to_remove = sorted(set(pid_to_entry.values()), reverse=True)
print(f'将要删除的条目数: {len(entry_indices_to_remove)}')

for idx in entry_indices_to_remove:
    start, end = entries[idx]
    # 标记该条目区域为空
    for j in range(start, end+1):
        lines[j] = None

# 重组：去除非空行
new_lines = []
deleted_count = 0
i = 0
while i < len(lines):
    if lines[i] is None:
        # 跳过连续的空行
        deleted_count += 1
        i += 1
        continue
    new_lines.append(lines[i])
    i += 1

# 但这样会多出空行，需要清理连续的空行
# 更稳定的方式：去掉标记为None的行，并清理多余空行
# 实际上最简单是：重新写文件时跳过None行
new_lines = []
prev_was_none = False
for i, line in enumerate(lines):
    if line is None:
        prev_was_none = True
        continue
    # 如果上一行是None（被删除）且当前行是空行，也跳过（删除多余的空行）
    if prev_was_none and (line == '' or line == '\r'):
        prev_was_none = False
        continue
    prev_was_none = False
    new_lines.append(line)

print(f'实际删除条目: {deleted_count}')

with open(inpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print(f'✅ 已更新 {inpath}')
