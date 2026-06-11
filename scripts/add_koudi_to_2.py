# -*- coding: utf-8 -*-
"""
把3个扣底盒结构加到2-扣底盒双插盒商品结构.txt
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 3个要追加的条目文本
entry1 = """═══ 天猫扣底盒（1 种格式, 共 1637 条）═══
[8] [x1637] 结构: 长宽【N*N】cm黄色;高度N【扣底盒】N个组
    样例: 长宽【15*15】cm 黄色;高度10【扣底盒】100个组
    pid=5419370666499"""

entry2 = """═══ 天猫彩色（2 种格式, 共 1637 条）═══
[9] [x986] 结构: 长宽【N*N】cm;高度Ncm【扣底盒】N个组
    样例: 长宽【11*11】cm;高度10cm【扣底盒】100个组
    pid=4886612768367

[10] [x651] 结构: 长宽【N*N】cm;高度Ncm【扣底纸盒】N个组
    样例: 长宽【15*15】cm;高度10cm【扣底纸盒】100个组
    pid=4891354397901"""

f2_path = r'D:\Desktop\2-扣底盒双插盒商品结构.txt'
with open(f2_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 追加到文件末尾
content += '\n' + entry1 + '\n\n' + entry2 + '\n'

# 重新编号并统计
lines = content.split('\n')
total_entries = 0
total_count = 0
new_lines = []
gidx = 0
for line in lines:
    m = re.match(r'(\s*)\[\d+\](\s*\[x\d+\]\s*结构:)', line)
    if m:
        gidx += 1
        total_entries += 1
        # 提取条数
        m2 = re.search(r'\[x(\d+)\]', line)
        if m2:
            total_count += int(m2.group(1))
        new_lines.append(f'{m.group(1)}[{gidx}]{m.group(2)}')
    else:
        # 更新店铺标题行的统计
        m = re.match(r'═══ (.+?)（(\d+) 种格式, 共 (\d+) 条）═══', line)
        if m:
            # 保留原样不重新算
            new_lines.append(line)
        else:
            new_lines.append(line)

# 更新头部统计
final_lines = []
for line in new_lines:
    if line.startswith('结构数:'):
        final_lines.append(f'结构数: {total_entries}, 总商品数: {total_count}')
    else:
        final_lines.append(line)

with open(f2_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_lines))

print(f'✅ 2号文件更新完成')
print(f'最终: {total_entries} 结构, {total_count} 条')

# 验证5个文件总结构数
# 读其他文件
other_files = {
    '1-定制商品结构.txt': r'D:\Desktop\1-定制商品结构.txt',
    '3-纸箱商品结构.txt': r'D:\Desktop\3-纸箱商品结构.txt',
    '4-剩余商品结构.txt': r'D:\Desktop\4-剩余商品结构.txt',
    '5-不属于定制的60个结构.txt': r'D:\Desktop\5-不属于定制的60个结构.txt',
}
total_structs = total_entries
for name, fpath in other_files.items():
    with open(fpath, 'r', encoding='utf-8') as f:
        m = re.search(r'结构数: (\d+)', f.read())
        if m:
            c = int(m.group(1))
            total_structs += c
            print(f'  {name}: {c} 结构')

print(f'\n5个文件合计: {total_structs} 结构 (应=1775)')
if total_structs == 1775:
    print('✅ 总数正确！')
else:
    print(f'❌ 差 {abs(total_structs - 1775)}')
