# -*- coding: utf-8 -*-
"""
全面审计脚本 - 对每个店铺的换绑文件进行校验
1. 读取源数据和生成的换绑文件
2. 统计编码类型分布 (标准/定制/EB/失败)
3. 抽样检查典型规格的解析结果
4. 检查明显错误 (尺寸异常、格式不对等)
"""
import sys, re, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

SOURCE = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
OUTDIR = r'D:\Desktop'

# 结构文件
STRUCT_FILES = [
    r'D:\Desktop\结构文本汇总.txt',
    r'D:\Desktop\品牌店剩余结构.txt',
    r'D:\Desktop\友尚剩余结构.txt',
]

# ===== 辅助函数 =====
def ms(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

def gn(s):
    return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))]

def parse_code(code):
    """解析商品编码为 (L, W, H, dk, mat, is_eb, is_custom)"""
    if code == '定制链接':
        return (None, None, None, None, None, False, True)
    m = re.match(r'(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)-(EB|3B)', code)
    if m:
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)),
                '外径', '纸箱', True, False)
    m = re.match(r'(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)-(.+?)-(.+)', code)
    if m:
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)),
                m.group(4), m.group(5), False, False)
    return None

def load_shop_names_from_source():
    """从源数据加载店铺名列表"""
    print('读取源数据...')
    df = pd.read_excel(SOURCE, dtype=str, header=None)
    data = df.iloc[1:].copy()
    data.columns = ['店', '商品id', '规格名', '规格id']
    shops = {}
    for s in data['店'].unique():
        s = s.strip()
        if s == '店铺名称':
            continue
        sd = data[data['店'] == s]
        shops[s] = len(sd)
    return shops

def audit_generated_file(shop_name):
    """审计单个店铺的换绑文件"""
    safe = shop_name.replace('/', '_').replace('\\', '_').replace(':', '_')
    fp = os.path.join(OUTDIR, f'换绑_{safe}.xlsx')
    
    result = {
        'shop': shop_name,
        'file_exists': os.path.exists(fp),
        'total': 0,
        'resolved': 0,
        'custom': 0,
        'eb': 0,
        'failed': 0,
        'samples': [],
        'suspicious': [],
        'codes': set(),
        'dk_dist': {},
        'mat_dist': {},
    }
    
    if not os.path.exists(fp):
        return result
    
    try:
        df = pd.read_excel(fp, dtype=str)
    except Exception as e:
        result['file_exists'] = False
        result['suspicious'].append(f'文件损坏: {e}')
        print(f'  文件损坏: {e}')
        return result
    
    df = df.iloc[2:].copy()  # 跳过标题行
    df.columns = ['店铺名称', '平台商品id', '平台规格id', '商品编码']
    
    total = 0
    for idx in range(len(df)):
        row = df.iloc[idx]
        code = str(row['商品编码'] or '').strip()
        if not code:
            continue
        total += 1
        
        if code == '定制链接':
            result['custom'] += 1
        else:
            parsed = parse_code(code)
            if parsed and parsed[6]:  # is_custom
                result['custom'] += 1
            elif parsed and parsed[5]:  # is_eb
                result['eb'] += 1
                result['resolved'] += 1
                dk = parsed[3]
                mat = parsed[4]
                result['dk_dist'][dk] = result['dk_dist'].get(dk, 0) + 1
                result['mat_dist'][mat] = result['mat_dist'].get(mat, 0) + 1
            elif parsed:
                result['resolved'] += 1
                dk = parsed[3]
                mat = parsed[4]
                result['dk_dist'][dk] = result['dk_dist'].get(dk, 0) + 1
                result['mat_dist'][mat] = result['mat_dist'].get(mat, 0) + 1
            else:
                result['failed'] += 1
                result['suspicious'].append(f'无法解析编码: {code}')
            
            result['codes'].add(code)
            
            # 检查异常尺寸
            if parsed and not parsed[6]:
                l, w, h = parsed[0], parsed[1], parsed[2]
                # 尺寸异常：小于1或大于200
                if (l and l < 0.5) or (w and w < 0.5) or (h and h < 0.5):
                    if len(result['samples']) < 5:
                        result['suspicious'].append(f'尺寸过小: {code}')
                if (l and l > 200) or (w and w > 200) or (h and h > 200):
                    if len(result['suspicious']) < 20:
                        result['suspicious'].append(f'尺寸过大: {code}')
    
    result['total'] = total
    return result

def load_expected_rules():
    """加载结构文件中的期望结果用于对比"""
    rules = {}
    for sf in STRUCT_FILES:
        if not os.path.exists(sf):
            continue
        with open(sf, 'r', encoding='utf-8') as f:
            content = f.read()
        # 提取所有店铺名
        shop_pattern = re.compile(r'═══\s*(.+?)\s*（\d+ 种格式')
        parts = shop_pattern.split(content)
        # parts = ['', shop_name, shop_content, shop_name2, ...]
        for i in range(1, len(parts), 2):
            shop_name = parts[i].strip()
            shop_content = parts[i+1] if i+1 < len(parts) else ''
            shop_rules = []
            # 找例:
            lines = shop_content.split('\n')
            for j, line in enumerate(lines):
                if line.strip().startswith('例:'):
                    raw = line.strip()[2:].strip()
                    # 解析例文 & 期望
                    t = raw.split()
                    num_idx = -1
                    for ti in range(len(t)-2):
                        if all(re.match(r'^\d+(?:\.\d+)?$', t[ti+k]) for k in range(3)):
                            num_idx = ti
                            break
                    if num_idx >= 0:
                        example = ' '.join(t[:num_idx])
                        expected = ' '.join(t[num_idx:])
                        shop_rules.append({
                            'example': example,
                            'expected': expected,
                            'skel': ms(example),
                        })
            if shop_name not in rules:
                rules[shop_name] = []
            rules[shop_name].extend(shop_rules)
    return rules

# ===== 主审计流程 =====
print('=' * 60)
print('全面审计: 14个店铺换绑文件')
print('=' * 60)

shops = load_shop_names_from_source()
print(f'\n源数据中店铺数: {len(shops)}')
print()

expected_rules = load_expected_rules()

all_results = []
for shop_name in sorted(shops.keys()):
    cnt = shops[shop_name]
    print(f'--- {shop_name} ({cnt} 条) ---')
    result = audit_generated_file(shop_name)
    all_results.append(result)
    
    if result['file_exists']:
        pct = (result['resolved'] + result['eb']) / max(result['total'], 1) * 100
        custom_pct = result['custom'] / max(result['total'], 1) * 100
        
        print(f'  文件: ✅ 存在')
        print(f'  总条数: {result["total"]}')
        print(f'  解析成功: {result["resolved"] + result["eb"]} ({pct:.1f}%)')
        print(f'    其中 EB/纸箱: {result["eb"]}')
        print(f'  定制链接: {result["custom"]} ({custom_pct:.1f}%)')
        print(f'  编码格式异常: {result["failed"]}')
        
        if result['dk_dist']:
            dk_str = ', '.join(f'{k}={v}' for k, v in sorted(result['dk_dist'].items()))
            print(f'  内外径分布: {dk_str}')
        if result['mat_dist']:
            mat_str = ', '.join(f'{k}={v}' for k, v in sorted(result['mat_dist'].items()))
            print(f'  材料分布: {mat_str}')
        
        if result['suspicious']:
            print(f'  可疑项 ({len(result["suspicious"])}):')
            for s in result['suspicious'][:10]:
                print(f'    ⚠️ {s}')
            if len(result['suspicious']) > 10:
                print(f'    ... 还有 {len(result["suspicious"])-10} 条')
        
        # 抽样展示
        if shop_name in expected_rules:
            rules = expected_rules[shop_name]
            print(f'  结构文件中: {len(rules)} 种格式')
        
        print()
    else:
        print(f'  文件: ❌ 未生成\n')

# ===== 汇总 =====
print('=' * 60)
print('汇总报告')
print('=' * 60)
print(f'{"店铺名称":30s} {"总条数":>8s} {"成功率":>7s} {"定制率":>7s} {"定制数":>6s}')
print('-' * 60)

total_rows = total_resolved = total_custom = 0
for r in sorted(all_results, key=lambda x: x['shop']):
    rows = r['total']
    resolved = r['resolved'] + r['eb']
    custom = r['custom']
    pct = f'{resolved / max(rows,1) * 100:.1f}%'
    cpct = f'{custom / max(rows,1) * 100:.1f}%'
    total_rows += rows
    total_resolved += resolved
    total_custom += custom
    flag = '✅' if resolved == rows else ('⚠️' if resolved / max(rows,1) >= 0.95 else '❌')
    print(f'{r["shop"]:30s} {rows:>8d} {pct:>7s} {cpct:>7s} {custom:>6d}  {flag}')

print('-' * 60)
total_pct = f'{total_resolved / max(total_rows,1) * 100:.1f}%'
total_cpct = f'{total_custom / max(total_rows,1) * 100:.1f}%'
print(f'{"总计":30s} {total_rows:>8d} {total_pct:>7s} {total_cpct:>7s} {total_custom:>6d}')

# ===== 输出详细报告 =====
report_path = os.path.join(OUTDIR, '审计报告_14店铺.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('三羊系统 - 14个店铺换绑文件审计报告\n')
    f.write('=' * 60 + '\n\n')
    for r in sorted(all_results, key=lambda x: x['shop']):
        f.write(f'【{r["shop"]}】\n')
        f.write(f'  文件: {"✅ 存在" if r["file_exists"] else "❌ 未生成"}\n')
        f.write(f'  总条数: {r["total"]}\n')
        if r['file_exists']:
            pct = (r['resolved'] + r['eb']) / max(r['total'], 1) * 100
            f.write(f'  成功解析: {r["resolved"] + r["eb"]} ({pct:.1f}%)\n')
            f.write(f'  纸箱EB: {r["eb"]}\n')
            f.write(f'  定制链接: {r["custom"]} ({r["custom"]/max(r["total"],1)*100:.1f}%)\n')
            f.write(f'  解析失败: {r["failed"]}\n')
            if r['suspicious']:
                f.write(f'  可疑项 ({len(r["suspicious"])}):\n')
                for s in r['suspicious'][:20]:
                    f.write(f'    {s}\n')
        f.write('\n')
    
    # 汇总
    f.write('=' * 60 + '\n')
    f.write('汇总\n')
    f.write('=' * 60 + '\n')
    f.write(f'{"店铺名称":30s} {"总条数":>8s} {"成功率":>7s} {"定制率":>7s}\n')
    f.write('-' * 55 + '\n')
    for r in sorted(all_results, key=lambda x: x['shop']):
        rows = r['total']
        resolved = r['resolved'] + r['eb']
        custom = r['custom']
        pct = f'{resolved / max(rows,1) * 100:.1f}%'
        cpct = f'{custom / max(rows,1) * 100:.1f}%'
        f.write(f'{r["shop"]:30s} {rows:>8d} {pct:>7s} {cpct:>7s}\n')
    f.write('-' * 55 + '\n')
    f.write(f'{"总计":30s} {total_rows:>8d} {total_pct:>7s} {total_cpct:>7s}\n')

print(f'\n详细报告已保存: {report_path}')
print(f'\n共审计 {len(all_results)} 个店铺, {total_rows} 条数据')
print(f'平均成功率: {total_pct}, 平均定制率: {total_cpct}')
