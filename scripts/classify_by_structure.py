# -*- coding: utf-8 -*-
"""
从原始商品所有格式.txt 出发，
按结构字符串分类，生成4个文件（放在桌面）：
1. 定制商品结构.txt
2. 扣底盒双插盒商品结构.txt
3. 纸箱商品结构.txt
4. 剩余商品结构.txt

规则：
- 定制：纯定制/珍珠棉/无3个尺寸数值
- 扣底盒双插盒：含"扣底"或"双插" + 有3个尺寸数值
- 纸箱：含"纸箱"或"五层" + 有3个尺寸数值
- 剩余：以上都不是

计数规则：N个/N层/N元/N装/N组/组/个组 不算数值N
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def count_dim_n(s):
    """
    计数代表实际长宽高的N（数值）。
    排除：N个、N层、N元、N装、N组、个组
    只计：乘号连接 N*N、NxN、N×N 中的N，以及 长N/宽N/高N/长度N/宽度N/高度N 中的N
    如果总N数 - 排除的N >= 3，认为有完整尺寸
    """
    total_n = s.count('N')
    
    # 排除非尺寸的N
    exclude = 0
    exclude += len(re.findall(r'N个', s))
    exclude += len(re.findall(r'N层', s))
    exclude += len(re.findall(r'N元', s))
    exclude += len(re.findall(r'N装', s))
    exclude += len(re.findall(r'N组', s))
    exclude += len(re.findall(r'个组', s))
    
    real_n = total_n - exclude
    return real_n >= 3

def parse_txt(path):
    """
    解析原始商品所有格式.txt，返回列表
    每个元素: dict {shop, count, skeleton, spec, pid}
    """
    sections = []
    current_shop = None
    current_count = 0
    current_skeleton = None
    current_spec = None
    current_pid = None
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            
            # 店铺标题行
            m = re.match(r'═══ (.+?)（(\d+) 种格式, 共 (\d+) 条）═══', line)
            if m:
                current_shop = m.group(1)
                continue
            
            # 格式行: [N] [xN] 结构: xxx
            m = re.match(r'\s*\[\d+\]\s*\[x(\d+)\]\s*结构:\s*(.+)', line)
            if m:
                current_count = int(m.group(1))
                current_skeleton = m.group(2).strip()
                current_spec = None
                current_pid = None
                continue
            
            # 样例行
            m = re.match(r'\s*样例:\s*(.+)', line)
            if m:
                current_spec = m.group(1).strip()
                continue
            
            # pid行
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
                continue
    
    return sections

def classify_section(s):
    """
    根据结构字符串分类
    返回: '定制' / '扣底盒' / '纸箱' / '剩余'
    """
    sk = s['skeleton']
    
    has_full_dims = count_dim_n(sk)
    
    # 含其他颜色（除黑/白/黄以外）→ 定制
    # 匹配：红色、蓝色、粉红色、绿色、紫色、牛皮色、原色、彩色 等
    # 排除：白色、黄色、黑色 + 双面纯色（黑&红这种有尺寸的不算颜色定制）
    other_colors = re.findall(r'[^黑白黄]色', sk)
    # 但 "双面纯色" 不算，它是有尺寸的
    has_other_color = any(c in sk for c in ['红色', '蓝色', '绿色', '紫色', '粉红', '彩色'])
    if has_other_color:
        return '定制'
    
    # 扣底盒/双插盒：必须含关键字 + 有3个尺寸数值
    if ('扣底' in sk or '双插' in sk) and has_full_dims:
        return '扣底盒'
    
    # 纸箱：必须含关键字 + 有3个尺寸数值
    if ('纸箱' in sk or '五层' in sk) and has_full_dims:
        return '纸箱'
    
    # 定制：没有3个尺寸数值
    if not has_full_dims:
        return '定制'
    
    return '剩余'

# 读取
src = r'D:\Desktop\原始商品所有格式.txt'
print('解析原始商品所有格式.txt ...')
all_sections = parse_txt(src)
print(f'共 {len(all_sections)} 个结构')

# 分类
classified = {'定制': [], '扣底盒': [], '纸箱': [], '剩余': []}
for s in all_sections:
    cat = classify_section(s)
    classified[cat].append(s)

# 统计
for cat in ['定制', '扣底盒', '纸箱', '剩余']:
    items = classified[cat]
    total_cnt = sum(x['count'] for x in items)
    print(f'{cat}: {len(items)} 种格式, 共 {total_cnt} 条')

total_check = sum(sum(x['count'] for x in classified[cat]) for cat in classified)
print(f'合计: {total_check} 条')

# 写文件（按店铺分组）
def write_file_grouped_by_shop(items, fpath, title):
    total_cnt = sum(x['count'] for x in items)
    
    # 按店铺分组
    by_shop = {}
    for s in items:
        by_shop.setdefault(s['shop'], []).append(s)
    
    # 店铺排序（按条数降序）
    shop_order = sorted(by_shop.keys(), key=lambda sh: sum(x['count'] for x in by_shop[sh]), reverse=True)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f'{title}\n')
        f.write(f'结构数: {len(items)}, 总商品数: {total_cnt}\n\n')
        
        global_idx = 0
        for shop in shop_order:
            shop_items = by_shop[shop]
            shop_total = sum(x['count'] for x in shop_items)
            # 店铺内按条数降序
            shop_items.sort(key=lambda x: -x['count'])
            
            f.write(f'═══ {shop}（{len(shop_items)} 种格式, 共 {shop_total} 条）═══\n')
            for s in shop_items:
                global_idx += 1
                f.write(f'[{global_idx}] [x{s["count"]}] 结构: {s["skeleton"]}\n')
                f.write(f'    样例: {s["spec"]}\n')
                f.write(f'    pid={s["pid"]}\n')
                f.write('\n')
    
    print(f'  ✅ {fpath}')

outdir = r'D:\Desktop'
write_file_grouped_by_shop(classified['定制'], f'{outdir}\\定制商品结构.txt', '定制商品结构')
write_file_grouped_by_shop(classified['扣底盒'], f'{outdir}\\扣底盒双插盒商品结构.txt', '扣底盒双插盒商品结构')
write_file_grouped_by_shop(classified['纸箱'], f'{outdir}\\纸箱商品结构.txt', '纸箱商品结构')
write_file_grouped_by_shop(classified['剩余'], f'{outdir}\\剩余商品结构.txt', '剩余商品结构')

print('\n✅ 全部完成！')
