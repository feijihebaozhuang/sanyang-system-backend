# -*- coding: utf-8 -*-
"""
gen_fix_all v4 - 每个店铺只检查结构精确匹配，未匹配的列出诊断
"""
import sys, re, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

SOURCE = r'D:\Desktop\未识别飞机盒_待分析.xlsx'

def make_skel(s): return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))
def get_nums(s): return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))]

# ========== 结构规则解析 ==========
def parse_exp(text):
    t = text.strip()
    if t in ('定制','定制链接'): return None
    m = re.match(r'(?:纸箱\s*[\(（]?\s*E?\s*B?\s*[\)）]?\s*)?(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(EB|3B|五层)', t)
    if m: return (int(float(m.group(1))),int(float(m.group(2))),int(float(m.group(3))),'外径','EB',True)
    if '纸箱' in t or '五层' in t: return None
    parts = t.split()
    if len(parts)>=4:
        try: l,w,h=int(float(parts[0])),int(float(parts[1])),int(float(parts[2]))
        except: return None
        meta=' '.join(parts[3:])
        dk='内径' if '内' in meta else '外径'
        if '白' in meta: mat='白色'
        elif '黑' in meta: mat='黑色'
        elif '红' in meta: mat='红色'
        elif '蓝' in meta: mat='蓝色'
        elif '超硬' in meta: mat='超硬'
        elif '特硬' in meta: mat='特硬'
        elif '优质' in meta: mat='优质'
        else: mat='特硬'
        return (l,w,h,dk,mat,'EB' in meta or '纸箱' in meta or parts[3] in ('EB','3B','五层'))
    if len(parts)==3:
        try: return (int(float(parts[0])),int(float(parts[1])),int(float(parts[2])),'外径','特硬',False)
        except: return None
    return None

def build_rule(example, exp_line):
    if exp_line is None: return {'custom':True}
    exp = parse_exp(exp_line)
    if exp is None:
        s=example.replace(' ','')
        eb_lw=re.search(r'长宽(\d+(?:\.\d+)?)\s*[*×xX*]\s*(\d+(?:\.\d+)?)', s)
        eb_h=re.search(r'高[度]?\s*\[?\s*(\d+(?:\.\d+)?)', s)
        if eb_lw and eb_h: exp=(int(float(eb_lw.group(1))),int(float(eb_lw.group(2))),int(float(eb_h.group(1))),'外径','EB',True)
        else: return {'custom':True}
    el,ew,eh,dk,mat,is_eb=exp
    ex_clean=example.replace(' ','')
    ex_vals=get_nums(ex_clean)
    if len(ex_vals)==0: return {'custom':True}
    h_ctx=set()
    for m in re.finditer(r'(\d+(?:\.\d+)?)',ex_clean):
        v=float(m.group()); s0=max(0,m.start()-3); e0=min(len(ex_clean),m.end()+3)
        if '高' in ex_clean[s0:e0]:
            for i,nv in enumerate(ex_vals):
                if abs(nv-v)<0.01: h_ctx.add(i); break
    used=set(); h_i=h_div=l_i=w_i=None; l_div=w_div=1; l_sub=w_sub=h_sub=0.0
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-eh)<0.01 and i in h_ctx: h_i=i;h_div=1;used.add(i);break
        elif abs(v/10-eh)<0.01 and i in h_ctx: h_i=i;h_div=10;used.add(i);break
    if h_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-eh)<0.01: h_i=i;h_div=1;used.add(i);break
            elif abs(v/10-eh)<0.01: h_i=i;h_div=10;used.add(i);break
    if h_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-eh)<=0.5: h_i=i;h_div=1;used.add(i);break
            elif abs(v/10-eh)<=0.5: h_i=i;h_div=10;used.add(i);break
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-el)<0.01: l_i=i;l_div=1;used.add(i);break
        elif abs(v/10-el)<0.01: l_i=i;l_div=10;used.add(i);break
    if l_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-el)<=0.5 or abs(v/10-el)<=0.5: l_i=i; l_div=10 if abs(v/10-el)<abs(v-el) else 1; used.add(i); break
    for i,v in enumerate(ex_vals):
        if i in used: continue
        if abs(v-ew)<0.01: w_i=i;w_div=1;used.add(i);break
        elif abs(v/10-ew)<0.01: w_i=i;w_div=10;used.add(i);break
    if w_i is None:
        for i,v in enumerate(ex_vals):
            if i in used: continue
            if abs(v-ew)<=0.5 or abs(v/10-ew)<=0.5: w_i=i; w_div=10 if abs(v/10-ew)<abs(v-ew) else 1; used.add(i); break
    m=re.search(r'长x宽【\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*】.*(?:高度|高)[\+＋]0\.5',ex_clean)
    if(l_i is None or w_i is None) and m:
        n1,p1=float(m.group(1)),float(m.group(2))
        if abs(int(round(n1-1.5))-el)<0.1 and abs(int(round(p1-0.5))-ew)<0.1:
            for i,v in enumerate(ex_vals):
                if abs(v-n1)<0.01 and l_i is None: l_i=i;l_div=1;l_sub=1.5;used.add(i)
                elif abs(v-p1)<0.01 and w_i is None: w_i=i;w_div=1;w_sub=0.5;used.add(i)
            dk='内径'
    m=re.search(r'长\*宽【\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)',ex_clean)
    if(l_i is None or w_i is None) and m:
        ov1,ov2=float(m.group(1)),float(m.group(2))
        for off_l in[1.5,1.0,0.5]:
            for off_w in[0.5,1.0,0.0]:
                if abs(int(round(ov1-off_l))-el)<0.1 and abs(int(round(ov2-off_w))-ew)<0.1:
                    for i,v in enumerate(ex_vals):
                        if abs(v-ov1)<0.01 and l_i is None: l_i=i;l_div=1;l_sub=off_l;used.add(i)
                        elif abs(v-ov2)<0.01 and w_i is None: w_i=i;w_div=1;w_sub=off_w;used.add(i)
                    dk='内径'; break
            if l_i and w_i: break
    if l_i is None or w_i is None or h_i is None: return {'custom':True}
    return {'l_i':l_i,'w_i':w_i,'h_i':h_i,'l_div':l_div,'w_div':w_div,'h_div':h_div,
            'l_sub':l_sub,'w_sub':w_sub,'h_sub':h_sub,'dk':dk,'mat':mat,'is_eb':is_eb}

def apply_rule(rule, spec):
    nums=get_nums(spec)
    if max(rule['l_i'],rule['w_i'],rule['h_i'])>=len(nums): return None
    lv=nums[rule['l_i']]/rule['l_div']-rule.get('l_sub',0)
    wv=nums[rule['w_i']]/rule['w_div']-rule.get('w_sub',0)
    hv=nums[rule['h_i']]/rule['h_div']-rule.get('h_sub',0)
    li,wi,hi=max(1,int(round(lv))),max(1,int(round(wv))),max(1,int(round(hv)))
    return f'{li}*{wi}*{hi}-EB' if rule['is_eb'] else f'{li}*{wi}*{hi}-{rule["dk"]}-{rule["mat"]}'

def load_struct_rules(fp):
    shops={}
    if not os.path.exists(fp): return shops
    with open(fp,'r',encoding='utf-8') as f: lines=f.readlines()
    cur=None; i=0
    while i<len(lines):
        l=lines[i].strip()
        m=re.match(r'═+\s*(.+?)\s*（\d+',l)
        if not m: m=re.match(r'═══\s*(.+?)\s*═══',l)
        if m: cur=m.group(1).strip(); shops[cur]={}; i+=1; continue
        m=re.match(r'\s*\[(\d+)\]\s*\[x(\d+)\]\s*(.+)',l)
        if m and cur:
            for j in range(i+1,min(i+5,len(lines))):
                ll=lines[j].strip()
                if ll.startswith('例:'):
                    raw=ll[2:].strip(); tokens=raw.split(); ni=-1
                    for ti in range(len(tokens)-2):
                        if all(re.match(r'^\d+(?:\.\d+)?$',tokens[ti+k]) for k in range(3)): ni=ti; break
                    if ni>=0: ex=' '.join(tokens[:ni]); exp=' '.join(tokens[ni:])
                    else:
                        ex=raw; exp=None
                        for k in range(j+1,min(i+5,len(lines))):
                            lk=lines[k].strip()
                            if lk and not lk.startswith('例:') and not lk.startswith('═') and not lk.startswith('['): exp=lk; break
                    if ex and exp:
                        sk=make_skel(ex); rule=build_rule(ex,exp)
                        if rule: shops[cur][sk]=rule
                    break
        i+=1
    return shops

STRUCT_FILES=[r'D:\Desktop\结构文本汇总.txt',r'D:\Desktop\品牌店剩余结构.txt',r'D:\Desktop\友尚剩余结构.txt']
all_rules={}
for sf in STRUCT_FILES:
    ss=load_struct_rules(sf)
    for sn,rs in ss.items():
        if sn in all_rules: all_rules[sn].update(rs)
        else: all_rules[sn]=rs

df=pd.read_excel(SOURCE,dtype=str,header=None)
data=df.iloc[1:].copy()
data.columns=['店','商品id','规格名','规格id']
data['店']=data['店'].str.strip()

print('='*80)
print(f'{"店铺名称":30s} {"总数":>6s} {"匹配":>6s} {"定制":>6s} {"%":>6s} {"未匹配骨架":>10s}')
print('='*80)
for shop_name in sorted([n for n in data['店'].unique() if n!='店铺名称']):
    sd=data[data['店']==shop_name]
    rules=all_rules.get(shop_name,{})
    total=len(sd); struct_ok=struct_eb=struct_cus=0
    # 统计
    for spec in sd['规格名']:
        skel=make_skel(str(spec).strip()); rule=rules.get(skel)
        if rule and not rule.get('custom'): struct_ok+=1
        elif rule and rule.get('custom'): struct_cus+=1
    missed=total-struct_ok-struct_cus
    pct=(struct_ok+struct_eb)/total*100
    flag='✅' if pct==100 else '⚠️' if missed<10 else '❌'
    print(f'{shop_name:30s} {total:>6d} {struct_ok:>6d} {struct_cus:>6d} {pct:>5.1f}% {missed:>8d} {flag}')
    
    if missed>0:
        # 显示缺失的模式
        unk={}
        for spec in sd['规格名']:
            skel=make_skel(str(spec).strip())
            if skel not in rules:
                if skel not in unk: unk[skel]={'cnt':0,'ex':str(spec).strip()}
                unk[skel]['cnt']+=1
        print(f'  缺失模式(前5):')
        for sk,m in sorted(unk.items(),key=lambda x:-x[1]['cnt'])[:5]:
            print(f'    [{m["cnt"]:>4d}] {m["ex"][:60]}...')

print('='*80)
print('注: ✅=100%  ⚠️=定制<10条  ❌=需处理')
