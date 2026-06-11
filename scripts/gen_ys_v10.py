# -*- coding: utf-8 -*-
"""
友尚 v10 - 支持公式模式（长x宽【NxP】→L-1.5,W-0.5）
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市友尚包装有限公司'
struct_file = r'D:\Desktop\友尚剩余结构.txt'

def _write_excel(path, codes):
    wb = oxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append([None, '商品对应表', None, None])
    ws.append(['店铺名称', '平台商品id', '平台规格id', '商品编码'])
    for r in codes:
        ws.append(list(r))
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 25
    wb.save(path)
    wb.close()

def get_nums(s):
    return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))]

def make_skel(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

def parse_expected(exp_str):
    s = exp_str.strip()
    if s == '定制': return None
    parts = s.split()
    if len(parts) >= 5 and parts[0] == '纸箱':
        return (int(float(parts[1])), int(float(parts[2])), int(float(parts[3])), '外径', 'EB', True)
    if len(parts) >= 4:
        l, w, h = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
        if len(parts) >= 5: return (l, w, h, parts[3], parts[4], False)
        last = parts[3]
        dk = '内径' if '内径' in last else '外径' if '外径' in last else '外径'
        mat = last.replace('内径','').replace('外径','') or '特硬'
        return (l, w, h, dk, mat, False)
    if len(parts) == 3:
        l, w, h = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
        return (l, w, h, '外径', '特硬', False)
    return None

def find_height_context_positions(ex_clean, ex_nums):
    h_set = set()
    for m in re.finditer(r'(\d+(?:\.\d+)?)', ex_clean):
        val = float(m.group())
        start = max(0, m.start()-3)
        end = min(len(ex_clean), m.end()+3)
        ctx = ex_clean[start:end]
        if '高' in ctx or '高度' in ctx:
            for i, v in enumerate(ex_nums):
                if abs(v - val) < 0.01 and i not in h_set:
                    h_set.add(i); break
    return h_set

def analyze(example, expected_str):
    """
    分析例文→期望的映射
    返回 (skel, rule)
    rule可以是:
      {'custom': True} - 定制
      {'l_i', 'w_i', 'h_i', 'l_div', 'w_div', 'h_div', 'dk', 'mat', 'is_eb'} - 标准索引模式
      {'l_i', 'w_i', 'h_i', 'l_sub', 'w_sub', 'h_sub', 'l_div', 'w_div', 'h_div', 'dk', 'mat', 'is_eb'} - 公式模式(值-偏移)
    """
    exp = parse_expected(expected_str)
    if exp is None: 
        skel_c = make_skel(example)
        return skel_c, {'custom': True}
    el, ew, eh, dk, mat, is_eb = exp
    ex_nums = get_nums(example)
    ex_clean = example.replace(' ', '')
    h_contexts = find_height_context_positions(ex_clean, ex_nums)
    
    h_i = h_div = None
    l_i = w_i = None
    l_div = w_div = 1
    l_sub = w_sub = h_sub = 0  # formula offsets
    used = set()
    
    # H高度
    for i, v in enumerate(ex_nums):
        if i in used: continue
        if (abs(v - eh) < 0.01 and i in h_contexts):
            h_i, h_div = i, 1; used.add(i); break
        elif (abs(v/10 - eh) < 0.01 and i in h_contexts):
            h_i, h_div = i, 10; used.add(i); break
    if h_i is None:
        for i, v in enumerate(ex_nums):
            if i in used: continue
            if abs(v - eh) < 0.01:
                h_i, h_div = i, 1; used.add(i); break
            elif abs(v/10 - eh) < 0.01:
                h_i, h_div = i, 10; used.add(i); break
    
    # L
    for i, v in enumerate(ex_nums):
        if i in used: continue
        if abs(v - el) < 0.01:
            l_i, l_div = i, 1; used.add(i); break
        elif abs(v/10 - el) < 0.01:
            l_i, l_div = i, 10; used.add(i); break
    # W
    for i, v in enumerate(ex_nums):
        if i in used: continue
        if abs(v - ew) < 0.01:
            w_i, w_div = i, 1; used.add(i); break
        elif abs(v/10 - ew) < 0.01:
            w_i, w_div = i, 10; used.add(i); break
    
    # 兜底
    if l_i is None:
        for i, v in enumerate(ex_nums):
            if i in used: continue
            if abs(v/10 - el) < 0.5 or abs(v - el) < 0.5:
                l_i = i; l_div = 10 if abs(v/10 - el) < abs(v - el) else 1; used.add(i); break
    if w_i is None:
        for i, v in enumerate(ex_nums):
            if i in used: continue
            if abs(v/10 - ew) < 0.5 or abs(v - ew) < 0.5:
                w_i = i; w_div = 10 if abs(v/10 - ew) < abs(v - ew) else 1; used.add(i); break
    
    # 特殊模式：长x宽【NxP】高度+0.5 → L=int(N-1.5),W=int(P-0.5)
    lxw_pat = re.compile(r'长x宽【\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*】.*(?:高度|高)[\+＋]0\.5')
    if l_i is None or w_i is None:
        lxw_m = lxw_pat.search(ex_clean)
        if lxw_m:
            lxw_N = float(lxw_m.group(1))
            lxw_P = float(lxw_m.group(2))
            calc_el = int(round(lxw_N - 1.5))
            calc_ew = int(round(lxw_P - 0.5))
            if calc_el == el and calc_ew == ew:
                for i, v in enumerate(ex_nums):
                    if abs(v - lxw_N) < 0.01 and l_i is None:
                        l_i = i; l_div = 1; l_sub = 1.5; used.add(i)
                    elif abs(v - lxw_P) < 0.01 and w_i is None:
                        w_i = i; w_div = 1; w_sub = 0.5; used.add(i)
                dk = '内径'
    
    if l_i is None or w_i is None or h_i is None:
        skel_c = make_skel(example)
        return skel_c, {'custom': True}
    
    skel = make_skel(example)
    rule = {
        'l_i': l_i, 'w_i': w_i, 'h_i': h_i,
        'l_div': l_div, 'w_div': w_div, 'h_div': h_div,
        'l_sub': l_sub, 'w_sub': w_sub, 'h_sub': h_sub,
        'dk': dk, 'mat': mat, 'is_eb': is_eb,
    }
    return skel, rule

def apply_rule(rule, spec):
    """根据规则从规格字符串提取编码"""
    nums = get_nums(spec.replace(' ', ''))
    need = max(rule['l_i'], rule['w_i'], rule['h_i'])
    if need >= len(nums): return None
    
    lv = nums[rule['l_i']] / rule['l_div'] - rule.get('l_sub', 0)
    wv = nums[rule['w_i']] / rule['w_div'] - rule.get('w_sub', 0)
    hv = nums[rule['h_i']] / rule['h_div'] - rule.get('h_sub', 0)
    
    li, wi, hi = max(1, int(round(lv))), max(1, int(round(wv))), max(1, int(round(hv)))
    
    if rule['is_eb']:
        return f'{li}*{wi}*{hi}-EB'
    return f'{li}*{wi}*{hi}-{rule["dk"]}-{rule["mat"]}'

# ===== 加载结构 =====
with open(struct_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

structs = {}
i = 0
while i < len(lines):
    line = lines[i].strip()
    m = re.match(r'\s*\[(\d+)\]\s*\[x(\d+)\]\s*(.+)', line)
    if m:
        for j in range(i+1, min(i+5, len(lines))):
            ll = lines[j].strip()
            if ll.startswith('例:'):
                example = ll[2:].strip()
                expected = None
                for k in range(j+1, min(i+5, len(lines))):
                    lk = lines[k].strip()
                    if lk and not lk.startswith('例:') and not lk.startswith('═') and not lk.startswith('['):
                        if re.search(r'\d', lk) or lk == '定制':
                            expected = lk; break
                if expected is not None:
                    skel, rule = analyze(example, expected)
                    if skel and rule:
                        structs[skel] = rule
                break
    i += 1

cus = sum(1 for v in structs.values() if v.get('custom'))
par = sum(1 for v in structs.values() if not v.get('custom'))
print(f'结构: {len(structs)}, 定制: {cus}, 可解析: {par}')

# 统计公式模式
formula_count = sum(1 for v in structs.values() if not v.get('custom') and (v.get('l_sub',0) != 0 or v.get('w_sub',0) != 0))
print(f'公式模式: {formula_count}')

# ===== 读取数据 =====
print('读取数据...')
df = pd.read_excel(source, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
sd = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(sd)} 条')

# ===== 执行 =====
codes = []
n_ok = n_zx = n_cus = n_fail = 0

for idx in range(len(sd)):
    row = sd.iloc[idx]
    shop_n = str(row['店铺名称'] or '').strip()
    pid = str(row['平台商品id'] or '').strip()
    spec = str(row['平台规格名称'] or '').strip()
    sid = str(row['平台规格id'] or '').strip()
    
    skel = make_skel(spec)
    rule = structs.get(skel)
    
    if rule is None:
        codes.append((shop_n, pid, sid, '定制链接')); n_fail += 1; continue
    if rule.get('custom'):
        codes.append((shop_n, pid, sid, '定制链接')); n_cus += 1; continue
    
    result = apply_rule(rule, spec)
    if result is None:
        codes.append((shop_n, pid, sid, '定制链接')); n_fail += 1; continue
    
    if rule['is_eb']:
        codes.append((shop_n, pid, sid, result)); n_zx += 1
    else:
        codes.append((shop_n, pid, sid, result)); n_ok += 1

print(f'正常: {n_ok}, 纸箱EB: {n_zx}, 定制: {n_cus}, 失败(当定制): {n_fail}')

out = r'D:\Desktop\换绑_深圳市友尚包装有限公司.xlsx'
_write_excel(out, codes)
print(f'DONE: {out}')
