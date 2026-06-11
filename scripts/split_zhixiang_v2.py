# -*- coding: utf-8 -*-
"""
从 4-纸箱商品结构.txt 拆成：
- 4-三层纸箱商品结构.txt
- 4a-五层纸箱商品结构.txt

判断规则：从每个条目的样例中看是几层
- 样例里含 "3层"/"三层"/"3 层" → 三层
- 样例里含 "5层"/"五层"/"5 层" → 五层
- 都没写 → 默认按结构关键词（"三层"/"五层"/"N层"）
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===== 直接解析原始商品所有格式.txt，从1789个中找出纸箱结构 =====
def parse_all_sections(path):
    sections = []
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    
    lines = raw.split('\n')
    current_shop = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'═══ (.+?)（(\d+) 种格式, 共 (\d+) 条）═══', line)
        if m:
            current_shop = m.group(1)
            i += 1
            continue
        
        m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:\s*(.*)', line)
        if m:
            count = int(m.group(1))
            skeleton = m.group(2).strip()
            spec = ''
            if i+1 < len(lines):
                m2 = re.match(r'\s*样例:\s*(.+)', lines[i+1])
                if m2:
                    spec = m2.group(1).strip()
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
            i += 3
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            continue
        i += 1
    
    return sections

src = r'D:\Desktop\原始商品所有格式.txt'
all_sections = parse_all_sections(src)
print(f'原始共 {len(all_sections)} 个结构')

# 找出所有纸箱结构（从4-纸箱商品结构.txt的分类逻辑）
zhixiang_items = []
for s in all_sections:
    sk = s['skeleton']
    if ('纸箱' in sk or '五层' in sk):
        # 检查有3个尺寸
        total_n = sk.count('N')
        exclude = 0
        exclude += len(re.findall(r'N个', sk))
        exclude += len(re.findall(r'N层', sk))
        exclude += len(re.findall(r'N元', sk))
        exclude += len(re.findall(r'N装', sk))
        exclude += len(re.findall(r'N组', sk))
        exclude += len(re.findall(r'个组', sk))
        if total_n - exclude >= 3:
            zhixiang_items.append(s)

print(f'纸箱结构: {len(zhixiang_items)} 个')

# 判断每层
san_items = []
wu_items = []

for s in zhixiang_items:
    text = s['spec'] + ' ' + s['skeleton']
    
    # 优先从样例判断
    is_wu = False
    is_san = False
    
    # 明确写五层/5层的
    if re.search(r'五层|5\s*层|五\s*层', text):
        is_wu = True
    # 明确写三层/3层的
    elif re.search(r'三层|3\s*层|三\s*层', text):
        is_san = True
    # 写 "N层" 的看样例实际数字
    elif 'N层' in s['skeleton']:
        spec_num = s['spec']
        m = re.search(r'(\d+)\s*层', spec_num)
        if m:
            if m.group(1) in ('3', '三'):
                is_san = True
            elif m.group(1) in ('5', '五'):
                is_wu = True
            else:
                is_wu = True  # 其他层数默认为五层
        else:
            is_wu = True  # 无法判断默认五层
    else:
        is_wu = True  # 默认五层
    
    if is_san:
        san_items.append(s)
    else:
        wu_items.append(s)

print(f'三层: {len(san_items)} 结构')
print(f'五层: {len(wu_items)} 结构')
print(f'合计: {len(san_items)+len(wu_items)} (应=40)')

# 写文件
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
write_file(san_items, f'{outdir}\\4-三层纸箱商品结构.txt', '三层纸箱商品结构')
write_file(wu_items, f'{outdir}\\4a-五层纸箱商品结构.txt', '五层纸箱商品结构')

# 验证
print(f'\n总数检查:')
print(f'三层: {len(san_items)} 结构, {sum(x["count"] for x in san_items)} 条')
print(f'五层: {len(wu_items)} 结构, {sum(x["count"] for x in wu_items)} 条')
print(f'合计: {len(san_items)+len(wu_items)} 结构, {sum(x["count"] for x in san_items)+sum(x["count"] for x in wu_items)} 条')
