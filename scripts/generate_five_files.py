# -*- coding: utf-8 -*-
"""
重新从原始商品所有格式.txt 出发生成5个文件：
1. 定制商品结构.txt（不含那60个）
2. 扣底盒双插盒商品结构.txt
3. 纸箱商品结构.txt
4. 剩余商品结构.txt
5. 不属于定制的60个结构.txt

5个文件 + 起 = 原始商品所有格式.txt 全部结构
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===== 要排除的 pid（不属于定制）=====
EXCLUDE_PIDS = set()
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
        EXCLUDE_PIDS.add(pid)

print(f'需要排除的 pid: {len(EXCLUDE_PIDS)} 个')

# ===== 计数函数 =====
def count_dim_n(s):
    """计数实际尺寸N，排除N个/N层/N元/N装/N组/个组"""
    total_n = s.count('N')
    exclude = 0
    exclude += len(re.findall(r'N个', s))
    exclude += len(re.findall(r'N层', s))
    exclude += len(re.findall(r'N元', s))
    exclude += len(re.findall(r'N装', s))
    exclude += len(re.findall(r'N组', s))
    exclude += len(re.findall(r'个组', s))
    return total_n - exclude >= 3

def has_other_color(sk):
    """含非黑/白/黄的其他颜色"""
    for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '彩色']:
        if c in sk:
            return True
    return False

# ===== 解析原始文件 =====
def parse_all_sections(path):
    sections = []
    current_shop = None
    current_count = 0
    current_skeleton = None
    current_spec = None
    current_pid = None
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            m = re.match(r'═══ (.+?)（(\d+) 种格式, 共 (\d+) 条）═══', line)
            if m:
                current_shop = m.group(1)
                continue
            m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:\s*(.+)', line)
            if m:
                current_count = int(m.group(1))
                current_skeleton = m.group(2).strip()
                current_spec = None
                current_pid = None
                continue
            m = re.match(r'\s*样例:\s*(.+)', line)
            if m:
                current_spec = m.group(1).strip()
                continue
            m = re.match(r'\s*pid=(.+)', line)
            if m:
                current_pid = m.group(1).strip()
                if current_shop and current_skeleton:
                    sections.append({
                        'shop': current_shop,
                        'count': current_count,
                        'skeleton': current_skeleton,
                        'spec': current_spec or '',
                        'pid': current_pid or ''
                    })
    return sections

src = r'D:\Desktop\原始商品所有格式.txt'
all_sections = parse_all_sections(src)
print(f'原始共 {len(all_sections)} 个结构')

# ===== 按规则分类 =====
classified = {'定制': [], '扣底盒': [], '纸箱': [], '剩余': []}
excluded = []  # 不属于定制的60个

for s in all_sections:
    sk = s['skeleton']
    pid = s['pid']
    has_dims = count_dim_n(sk)
    is_other_color = has_other_color(sk)
    
    # 扣底盒/双插盒
    if ('扣底' in sk or '双插' in sk) and has_dims:
        classified['扣底盒'].append(s)
        continue
    
    # 纸箱
    if ('纸箱' in sk or '五层' in sk) and has_dims:
        classified['纸箱'].append(s)
        continue
    
    # 其他颜色 → 定制
    if is_other_color:
        classified['定制'].append(s)
        continue
    
    # 没尺寸 → 定制
    if not has_dims:
        classified['定制'].append(s)
        continue
    
    # 剩余
    classified['剩余'].append(s)

# 从定制中挑出60个
final_custom = []
for s in classified['定制']:
    if s['pid'] in EXCLUDE_PIDS:
        excluded.append(s)
    else:
        final_custom.append(s)

print(f'\n--- 分类结果 ---')
for cat in ['定制', '扣底盒', '纸箱', '剩余']:
    items = classified[cat]
    print(f'{cat}: {len(items)} 结构')

print(f'从定制排除(60个): {len(excluded)} 结构')
print(f'最终定制: {len(final_custom)} 结构')

# 验证总数
total_check = len(final_custom) + len(classified['扣底盒']) + len(classified['纸箱']) + len(classified['剩余']) + len(excluded)
print(f'\n5个文件合计: {total_check} 结构 (应=1775)')
if total_check == 1775:
    print('✅ 结构数正确！')
else:
    print(f'❌ 差 {abs(total_check - 1775)}')

# ===== 写文件 =====
def write_file(items, fpath, title):
    by_shop = {}
    for s in items:
        by_shop.setdefault(s['shop'], []).append(s)
    shop_order = sorted(by_shop.keys(), key=lambda sh: sum(x['count'] for x in by_shop[sh]), reverse=True)
    total_cnt = sum(x['count'] for x in items)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f'{title}\n')
        f.write(f'结构数: {len(items)}, 总商品数: {total_cnt}\n\n')
        gidx = 0
        for shop in shop_order:
            shop_items = by_shop[shop]
            shop_items.sort(key=lambda x: -x['count'])
            shop_total = sum(x['count'] for x in shop_items)
            f.write(f'═══ {shop}（{len(shop_items)} 种格式, 共 {shop_total} 条）═══\n')
            for s in shop_items:
                gidx += 1
                f.write(f'[{gidx}] [x{s["count"]}] 结构: {s["skeleton"]}\n')
                f.write(f'    样例: {s["spec"]}\n')
                f.write(f'    pid={s["pid"]}\n')
                f.write('\n')
    print(f'  ✅ {fpath}')

outdir = r'D:\Desktop'
write_file(final_custom, f'{outdir}\\1-定制商品结构.txt', '定制商品结构')
write_file(classified['扣底盒'], f'{outdir}\\2-扣底盒双插盒商品结构.txt', '扣底盒双插盒商品结构')
write_file(classified['纸箱'], f'{outdir}\\3-纸箱商品结构.txt', '纸箱商品结构')
write_file(classified['剩余'], f'{outdir}\\4-剩余商品结构.txt', '剩余商品结构')
write_file(excluded, f'{outdir}\\5-不属于定制的60个结构.txt', '不属于定制的60个结构')

print('\n✅ 全部完成！')
