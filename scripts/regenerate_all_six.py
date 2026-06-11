# -*- coding: utf-8 -*-
"""
从原始商品所有格式.txt 出发生成6个文件（结构完整）：
1-定制商品结构.txt
2-扣底盒商品结构.txt  (含"扣底"不含"双插")
3-双插盒商品结构.txt  (含"双插")
4-纸箱商品结构.txt
5-剩余商品结构.txt
6-不属于定制的60个结构.txt (不含已移到2的3个)

所有结构字段完整保留！
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===== 要排除的 pid（从定制移到另外分类）=====
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

# 扣底盒pid（移到2号文件）
KOUDI_PIDS = {'5419370666499', '4886612768367', '4891354397901'}
# 排除中扣掉扣底盒，剩下的才算真正的"不属于定制"
REAL_EXCLUDE = EXCLUDE_PIDS - KOUDI_PIDS

print(f'排除pid总数: {len(EXCLUDE_PIDS)}, 其中扣底盒: {len(KOUDI_PIDS)}, 真正排除: {len(REAL_EXCLUDE)}')

# ===== 计数 =====
def count_dim_n(s):
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
    for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '彩色']:
        if c in sk:
            return True
    return False

# ===== 解析原始文件（保留完整格式）=====
def parse_all_sections(path):
    """返回 list of dict，保留原始行文本"""
    sections = []
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    
    # 按条目逐个解析
    lines = raw.split('\n')
    current_shop = None
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 店铺标题
        m = re.match(r'═══ (.+?)（(\d+) 种格式, 共 (\d+) 条）═══', line)
        if m:
            current_shop = m.group(1)
            i += 1
            continue
        
        # 条目行 [N] [xN] 结构: xxx
        m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:\s*(.*)', line)
        if m:
            count = int(m.group(1))
            skeleton = m.group(2).strip()
            # 下一行样例
            spec = ''
            if i+1 < len(lines):
                m2 = re.match(r'\s*样例:\s*(.+)', lines[i+1])
                if m2:
                    spec = m2.group(1).strip()
            # 下下行pid
            pid = ''
            if i+2 < len(lines):
                m3 = re.match(r'\s*pid=(.+)', lines[i+2])
                if m3:
                    pid = m3.group(1).strip()
            
            sections.append({
                'shop': current_shop or '(无名)',
                'count': count,
                'skeleton': skeleton,
                'spec': spec,
                'pid': pid
            })
            i += 3  # 跳过3行（结构+样例+pid）
            # 跳过空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            continue
        
        i += 1
    
    return sections

src = r'D:\Desktop\原始商品所有格式.txt'
all_sections = parse_all_sections(src)
print(f'原始共 {len(all_sections)} 个结构')

# ===== 分类 =====
custom_items = []
koudi_items = []
shuangcha_items = []
zhixiang_items = []
shengyu_items = []
exclude_items = []  # 真正不属于定制的60个
move_to_koudi_items = []  # 从排除移到扣底盒的3个

for s in all_sections:
    sk = s['skeleton']
    pid = s['pid']
    has_dims = count_dim_n(sk)
    is_other_color = has_other_color(sk)
    
    category = None
    
    # 扣底盒
    if '扣底' in sk and has_dims:
        category = '扣底盒'
    # 双插盒
    elif '双插' in sk and has_dims:
        category = '双插盒'
    # 纸箱
    elif ('纸箱' in sk or '五层' in sk) and has_dims:
        category = '纸箱'
    # 其他颜色→定制
    elif is_other_color:
        category = '定制'
    # 没尺寸→定制
    elif not has_dims:
        category = '定制'
    else:
        category = '剩余'
    
    # 检查是否在排除列表
    if pid in KOUDI_PIDS:
        move_to_koudi_items.append(s)
        continue
    
    if pid in REAL_EXCLUDE:
        exclude_items.append(s)
        continue
    
    if category == '扣底盒':
        koudi_items.append(s)
    elif category == '双插盒':
        shuangcha_items.append(s)
    elif category == '纸箱':
        zhixiang_items.append(s)
    elif category == '定制':
        custom_items.append(s)
    elif category == '剩余':
        shengyu_items.append(s)

# 把3个扣底盒pid的加入扣底盒
koudi_items.extend(move_to_koudi_items)

print(f'\n分类结果:')
print(f'定制: {len(custom_items)} 结构')
print(f'扣底盒: {len(koudi_items)} 结构')
print(f'双插盒: {len(shuangcha_items)} 结构')
print(f'纸箱: {len(zhixiang_items)} 结构')
print(f'剩余: {len(shengyu_items)} 结构')
print(f'不属于定制的60个: {len(exclude_items)} 结构')
print(f'移到扣底盒的3个: {len(move_to_koudi_items)} 结构')

total_check = len(custom_items) + len(koudi_items) + len(shuangcha_items) + len(zhixiang_items) + len(shengyu_items) + len(exclude_items)
print(f'\n6个文件合计: {total_check} 结构 (应=1775)')
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
    print(f'  ✅ {fpath}: {len(items)} 结构, {total_cnt} 条')

outdir = r'D:\Desktop'
write_file(custom_items, f'{outdir}\\1-定制商品结构.txt', '定制商品结构')
write_file(koudi_items, f'{outdir}\\2-扣底盒商品结构.txt', '扣底盒商品结构')
write_file(shuangcha_items, f'{outdir}\\3-双插盒商品结构.txt', '双插盒商品结构')
write_file(zhixiang_items, f'{outdir}\\4-纸箱商品结构.txt', '纸箱商品结构')
write_file(shengyu_items, f'{outdir}\\5-剩余商品结构.txt', '剩余商品结构')
write_file(exclude_items, f'{outdir}\\6-不属于定制的60个结构.txt', '不属于定制的60个结构')

print('\n✅ 全部完成！')
