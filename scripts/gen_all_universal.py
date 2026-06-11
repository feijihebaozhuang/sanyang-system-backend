# -*- coding: utf-8 -*-
"""
万能店铺解析器 v2.0 - 结构驱动法批量解析所有店铺
"""
import sys, re, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

SOURCE = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
OUTDIR = r'D:\Desktop'
STRUCT_FILES = [
    r'D:\Desktop\结构文本汇总.txt',
    r'D:\Desktop\品牌店剩余结构.txt',
    r'D:\Desktop\友尚剩余结构.txt',
]

def get_nums_vals(s):
    return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))]

def get_nums_pos(s):
    return [(m.start(), float(m.group())) for m in re.finditer(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))]

def make_skel(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))

def _write_excel(path, codes):
    wb = oxl.Workbook(); ws = wb.active; ws.title = 'Sheet1'
    ws.append([None, '商品对应表', None, None])
    ws.append(['店铺名称', '平台商品id', '平台规格id', '商品编码'])
    for r in codes: ws.append(list(r))
    wb.save(path); wb.close()

def parse_expected_text(text):
    """解析预期文本。返回 (l,w,h,dk,mat,is_eb,is_custom)"""
    t = text.strip().replace('\t', ' ')
    if t in ('定制', '定制链接'): return (0,0,0,'','',False,True)
    m = re.match(r'(?:纸箱\s*[\(（]?\s*E?\s*B?\s*[\)）]?\s*)?(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(EB|3B|E\s*B|五层)', t)
    if m: return (float(m.group(1)),float(m.group(2)),float(m.group(3)),'外径','EB',True,False)
    parts = [p for p in t.split() if p]
    if len(parts) < 3: return (0,0,0,'','',False,True)
    try: l,w,h = float(parts[0]),float(parts[1]),float(parts[2])
    except: return (0,0,0,'','',False,True)
    meta = ' '.join(parts[3:])
    if '内' in meta and '外' not in meta: dk='内径'
    elif '外' in meta: dk='外径'
    else: dk='外径'
    if '白' in meta: mat='白色'
    elif '黑' in meta: mat='黑色'
    elif '红' in meta: mat='红色'
    elif '蓝' in meta: mat='蓝色'
    elif '超硬' in meta: mat='超硬'
    elif '特硬' in meta: mat='特硬'
    elif '优质' in meta: mat='优质'
    elif '特' in meta: mat='特硬'
    else: mat='特硬'
    return (l,w,h,dk,mat,False,False)

def build_rule(example, expected):
    el, ew, eh, dk, mat, is_eb, is_custom = parse_expected_text(expected)
    if is_custom: return {'custom': True}
    ex_clean = example.replace(' ', '')
    ex_vals = get_nums_vals(ex_clean)
    if len(ex_vals) == 0: return {'custom': True}
    h_ctx = set()
    for m in re.finditer(r'(\d+(?:\.\d+)?)', ex_clean):
        v = float(m.group())
        s,e = max(0,m.start()-3), min(len(ex_clean),m.end()+3)
        if '高' in ex_clean[s:e]:
            for i,nv in enumerate(ex_vals):
                if abs(nv-v)<0.01: h_ctx.add(i); break
    used=set(); h_i=h_div=l_i=w_i=None; l_div=w_div=1; l_sub=w_sub=h_sub=0.0
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-eh)<0.01 and i in h_ctx: h_i,h_div=i,1; used.add(i); break
        elif abs(v/10-eh)<0.01 and i in h_ctx: h_i,h_div=i,10; used.add(i); break
    if h_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-eh)<0.01: h_i,h_div=i,1; used.add(i); break
            elif abs(v/10-eh)<0.01: h_i,h_div=i,10; used.add(i); break
    if h_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-eh)<0.5: h_i,h_div=i,1; used.add(i); break
            elif abs(v/10-eh)<0.5: h_i,h_div=i,10; used.add(i); break
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-el)<0.01: l_i,l_div=i,1; used.add(i); break
        elif abs(v/10-el)<0.01: l_i,l_div=i,10; used.add(i); break
    if l_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-el)<0.5 or abs(v/10-el)<0.5:
                l_i=i; l_div=10 if abs(v/10-el)<abs(v-el) else 1; used.add(i); break
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-ew)<0.01: w_i,w_div=i,1; used.add(i); break
        elif abs(v/10-ew)<0.01: w_i,w_div=i,10; used.add(i); break
    if w_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-ew)<0.5 or abs(v/10-ew)<0.5:
                w_i=i; w_div=10 if abs(v/10-ew)<abs(v-ew) else 1; used.add(i); break
    lxw_re=re.compile(r'长x宽【\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*】.*(?:高度|高)[\+＋]0\.5')
    if l_i is None or w_i is None:
        m=lxw_re.search(ex_clean)
        if m:
            n1,p1=float(m.group(1)),float(m.group(2))
            if abs(int(round(n1-1.5))-el)<0.1 and abs(int(round(p1-0.5))-ew)<0.1:
                for i,v in enumerate(ex_vals):
                    if abs(v-n1)<0.01 and l_i is None: l_i=i;l_div=1;l_sub=1.5;used.add(i)
                    elif abs(v-p1)<0.01 and w_i is None: w_i=i;w_div=1;w_sub=0.5;used.add(i)
                dk='内径'
    lw_outer=re.compile(r'长\*宽【\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)')
    if l_i is None or w_i is None:
        m=lw_outer.search(ex_clean)
        if m:
            ov1,ov2=float(m.group(1)),float(m.group(2))
            for off_l in [1.5,1.0,0.5]:
                for off_w in [0.5,1.0,0.0]:
                    if abs(int(round(ov1-off_l))-el)<0.1 and abs(int(round(ov2-off_w))-ew)<0.1:
                        for i,v in enumerate(ex_vals):
                            if abs(v-ov1)<0.01 and l_i is None: l_i=i;l_div=1;l_sub=off_l;used.add(i)
                            elif abs(v-ov2)<0.01 and w_i is None: w_i=i;w_div=1;w_sub=off_w;used.add(i)
                        dk='内径'; break
                if l_i and w_i: break
    if l_i is None or w_i is None or h_i is None: return {'custom': True}
    return {'l_i':l_i,'w_i':w_i,'h_i':h_i,'l_div':l_div,'w_div':w_div,'h_div':h_div,
            'l_sub':l_sub,'w_sub':w_sub,'h_sub':h_sub,'dk':dk,'mat':mat,'is_eb':is_eb}

def apply_rule(rule, spec):
    nums = get_nums_vals(spec)
    if max(rule['l_i'],rule['w_i'],rule['h_i']) >= len(nums): return None
    lv = nums[rule['l_i']]/rule['l_div']-rule.get('l_sub',0)
    wv = nums[rule['w_i']]/rule['w_div']-rule.get('w_sub',0)
    hv = nums[rule['h_i']]/rule['h_div']-rule.get('h_sub',0)
    return f'{max(1,int(round(lv)))}*{max(1,int(round(wv)))}*{max(1,int(round(hv)))}-{"EB" if rule["is_eb"] else rule["dk"]}-{rule["mat"]}' if not rule['is_eb'] else f'{max(1,int(round(lv)))}*{max(1,int(round(wv)))}*{max(1,int(round(hv)))}-EB'

def is_numeric_token(t):
    return bool(re.match(r'^\d+(?:\.\d+)?$', t))

def split_example_expected(raw_text):
    """尝试在一行内拆分例文和预期输出。返回 (example, expected) 或 (None, None)"""
    tokens = raw_text.split()
    for ti in range(len(tokens)-2):
        if all(is_numeric_token(tokens[ti+k]) for k in range(3)):
            example = ' '.join(tokens[:ti])
            expected = ' '.join(tokens[ti:])
            return (example, expected)
    # 如果没找到3个连续数字，但行尾是"定制"或"定制链接"
    ct = raw_text.strip()
    if ct.endswith('定制') or ct.endswith('定制链接'):
        idx = max(ct.rfind('定制'), ct.rfind('定制链接'))
        if idx > 10:
            return (ct[:idx].strip(), ct[idx:].strip())
    return (None, None)

# ===== 解析结构文件 =====
def parse_structure_file(filepath):
    if not os.path.exists(filepath): return {}
    with open(filepath,'r',encoding='utf-8') as f: lines = f.readlines()
    shops = {}; current_shop = None; i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r'═+\s*(.+?)\s*（\d+', line)
        if not m: m = re.match(r'═══\s*(.+?)\s*═══', line)
        if m:
            current_shop = m.group(1).strip()
            shops[current_shop] = {}
            i += 1; continue
        m = re.match(r'\s*\[(\d+)\]\s*\[x(\d+)\]\s*(.+)', line)
        if m and current_shop:
            example = None; expected = None
            for j in range(i+1, min(i+5, len(lines))):
                ll = lines[j].strip()
                if ll.startswith('例:'):
                    raw = ll[2:].strip()
                    # 先尝试同行拆分
                    ex_try, exp_try = split_example_expected(raw)
                    if ex_try and exp_try:
                        example, expected = ex_try, exp_try
                    else:
                        example = raw
                        # 下一行作为预期行
                        for k in range(j+1, min(i+5, len(lines))):
                            lk = lines[k].strip()
                            if lk and not lk.startswith('例:') and not lk.startswith('═') and not lk.startswith('['):
                                expected = lk; break
                    break
            if example and expected:
                skel = make_skel(example)
                rule = build_rule(example, expected)
                if rule: shops[current_shop][skel] = rule
        i += 1
    return shops

# ===== 主流程 =====
print('='*60)
all_shops = {}
for sf in STRUCT_FILES:
    print(f'\n结构: {os.path.basename(sf)}')
    shop_data = parse_structure_file(sf)
    for sn, rules in shop_data.items():
        if sn in all_shops: all_shops[sn].update(rules)
        else: all_shops[sn] = rules
        cus = sum(1 for r in rules.values() if r.get('custom'))
        pars = sum(1 for r in rules.values() if not r.get('custom'))
        print(f'  {sn}: {len(rules)} ({pars}解析, {cus}定制)')

print(f'\n总店铺: {len(all_shops)}')
print(f'\n读源...')
df = pd.read_excel(SOURCE, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店铺名称','平台商品id','平台规格名称','平台规格id']
data['店铺名称'] = data['店铺名称'].str.strip()

to=te=tc=tf=0
for shop_name in sorted(all_shops.keys()):
    rules = all_shops[shop_name]
    sd = data[data['店铺名称']==shop_name].copy()
    if len(sd)==0: print(f'\n❌ 源无: {shop_name}'); continue
    codes=[]; no=ne=nc=nf=0
    for idx in range(len(sd)):
        row=sd.iloc[idx]; pid=str(row['平台商品id']or'').strip()
        spec=str(row['平台规格名称']or'').strip(); sid=str(row['平台规格id']or'').strip()
        skel=make_skel(spec); rule=rules.get(skel)
        if rule is None: codes.append((shop_name,pid,sid,'定制链接')); nf+=1; continue
        if rule.get('custom'): codes.append((shop_name,pid,sid,'定制链接')); nc+=1; continue
        result=apply_rule(rule,spec)
        if result is None: codes.append((shop_name,pid,sid,'定制链接')); nf+=1; continue
        if rule['is_eb']: codes.append((shop_name,pid,sid,result)); ne+=1
        else: codes.append((shop_name,pid,sid,result)); no+=1
    to+=no; te+=ne; tc+=nc; tf+=nf
    total=no+ne+nc+nf
    safe=shop_name.replace('/','_').replace('\\','_').replace(':','_')
    _write_excel(os.path.join(OUTDIR,f'换绑_{safe}.xlsx'), codes)
    pct=(no+ne)/total*100
    flag=' ✅' if pct==100 else f' ⚠️定制{nc}'
    print(f'  {shop_name:25s} {total:>6d} 正常{no:>6d} EB{ne:>4d} 定制{nc:>5d} 失败{nf:>3d}  {pct:>5.1f}%{flag}')

total_all=to+te+tc+tf
print(f'\n总计: {total_all}, 正常:{to}({to/total_all*100:.1f}%), EB:{te}, 定制:{tc}, 失败:{tf}')
