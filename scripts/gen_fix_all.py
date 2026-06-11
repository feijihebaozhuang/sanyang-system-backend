# -*- coding: utf-8 -*-
"""
gen_v8.py - 极简版：结构匹配(fast)+特定解析+兜底
"""
import sys,re,os
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import pandas as pd,openpyxl as oxl
SOURCE=r'D:\Desktop\未识别飞机盒_待分析.xlsx';OUTDIR=r'D:\Desktop'

def ms(s):return re.sub(r'\d+\.?\d*','N',re.sub(r'\s+','',s))
def gn(s):return[float(x)for x in re.findall(r'(\d+(?:\.\d+)?)',s.replace(' ',''))]

def xls(p,c):
    wb=oxl.Workbook();ws=wb.active;ws.title='Sheet1'
    ws.append([None,'商品对应表',None,None])
    ws.append(['店铺名称','平台商品id','平台规格id','商品编码'])
    for r in c:ws.append(list(r))
    wb.save(p);wb.close()

# ===== 加载结构文件规则(极速) =====
import json
def load_rules_fast(fp):
    shops={}
    if not os.path.exists(fp):return shops
    with open(fp,'r',encoding='utf-8')as f:lines=f.readlines()
    cur=None
    for i,line in enumerate(lines):
        l=line.strip()
        m=re.match(r'═+\s*(.+?)\s*（\d+',l)
        if not m:m=re.match(r'═══\s*(.+?)\s*═══',l)
        if m:cur=m.group(1).strip();shops[cur]={};continue
        m=re.match(r'\s*\[(\d+)\]\s*\[x(\d+)\]\s*(.+)',l)
        if m and cur:
            # 下一行的例文
            if i+1<len(lines):
                nxt=lines[i+1].strip()
                if nxt.startswith('例:'):
                    raw=nxt[2:].strip()
                    # 找3个连续数字
                    t=raw.split()
                    ni=-1
                    for ti in range(len(t)-2):
                        if all(re.match(r'^\d+(?:\.\d+)?$',t[ti+k])for k in range(3)):ni=ti;break
                    if ni>=0:
                        ex=' '.join(t[:ni])
                        exp=' '.join(t[ni:])
                        sk=ms(ex)
                        # 判断是否定制
                        if exp.strip() in('定制','定制链接'):shops[cur][sk]={'custom':True}
                        else:shops[cur][sk]={'known':True}
    return shops

ALL_R={}
for sf in[r'D:\Desktop\结构文本汇总.txt',r'D:\Desktop\品牌店剩余结构.txt',r'D:\Desktop\友尚剩余结构.txt']:
    for sn,rs in load_rules_fast(sf).items():
        ALL_R.setdefault(sn,{}).update(rs)
    print(f'  加载 {os.path.basename(sf)}: {sum(len(v) for v in load_rules_fast(sf).values())} 条定制标记')

# ===== 店铺解析器 =====
def dk(s):return'内径'if re.search(r'内[径寸]',s) and not re.search(r'外[径寸]',s)else'外径'
def mat(s):
    if'超硬'in s:return'超硬'
    if'白色'in s or'双面白'in s or'双白色'in s:return'白色'
    if'黑色'in s or'双面黑'in s:return'黑色'
    if'红色'in s or'双面红'in s:return'红色'
    if'蓝色'in s:return'蓝色'
    if'优质'in s:return'优质'
    if'白'in s:return'白色'
    if'黑'in s:return'黑色'
    if'红'in s:return'红色'
    return'特硬'

def p_jx(s):
    """俊鑫"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s)
    m=re.search(r'【高(\d+(?:\.\d+)?)】\s*;?\s*(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x高',s)
    if m:return(round(float(m.group(2))),round(float(m.group(3))),round(float(m.group(1))),dk_,mat_)
    m=re.search(r'【高(\d+(?:\.\d+)?)】.*?(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x高',s)
    if m:return(round(float(m.group(2))),round(float(m.group(3))),round(float(m.group(1))),dk_,mat_)
    # 【N*N】mm;高【Nmm】
    m=re.search(r'【(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)】\s*mm',s)
    mh=re.search(r'高【(\d+(?:\.\d+)?)\s*mm',s)
    if m and mh:return(round(float(m.group(1))/10),round(float(m.group(2))/10),round(float(mh.group(1))/10),dk_,mat_)
    # 【N】mm长;【N】mm宽 (含])
    ml=re.search(r'【(\d+(?:\.\d+)?)】?\s*mm\s*长',s)
    mw=re.search(r'【(\d+(?:\.\d+)?)】?\s*mm\s*宽',s)
    mh=re.search(r'高【(\d+(?:\.\d+)?)\s*mm',s)
    if mh and ml and mw:return(round(float(ml.group(1))/10),round(float(mw.group(1))/10),round(float(mh.group(1))/10),dk_,mat_)
    if mh and ml:
        ali=re.findall(r'(\d+(?:\.\d+)?)\s*mm',s)
        if len(ali)>=2:return(round(float(ml.group(1))/10),round(float(ali[1])/10),round(float(mh.group(1))/10),dk_,mat_)
    # N*N【长*宽mm】
    m=re.search(r'(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)\s*【',s)
    if m:
        hh=re.search(r'高【(\d+(?:\.\d+)?)\s*mm',s)
        if hh:return(round(float(m.group(1))/10),round(float(m.group(2))/10),round(float(hh.group(1))/10),dk_,mat_)
        al=re.findall(r'(\d+(?:\.\d+)?)\s*mm',s)
        for hc in reversed(al):
            if abs(float(hc)-float(m.group(1)))>0.01 and abs(float(hc)-float(m.group(2)))>0.01:
                return(round(float(m.group(1))/10),round(float(m.group(2))/10),round(float(hc)/10),dk_,mat_)
    return None

def p_dx(s):
    """当下家"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s)
    mw=re.search(r'宽\s*(\d+(?:\.\d+)?)\s*\[',s)
    ml=re.search(r'长\s*(\d+(?:\.\d+)?)\s*mm',s)
    mh=re.search(r'高\s*(\d+(?:\.\d+)?)\s*mm',s)
    if mw and ml and mh:return(round(float(ml.group(1))/10),round(float(mw.group(1))/10),round(float(mh.group(1))/10),dk_,mat_)
    mh2=re.search(r'(\d+(?:\.\d+)?)\s*cm\s*内高',s);mlw=re.search(r'(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)\s*【长宽',s)
    if mh2 and mlw:return(round(float(mlw.group(1))),round(float(mlw.group(2))),round(float(mh2.group(1))),dk_,mat_)
    mh3=re.search(r'(\d+(?:\.\d+)?)\s*mm\s*高',s);mlw3=re.search(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*mm\s*长宽',s)
    if mh3 and mlw3:return(round(float(mlw3.group(1))/10),round(float(mlw3.group(2))/10),round(float(mh3.group(1))/10),dk_,mat_)
    return None

def p_yr(s):
    """亚润"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s)
    ml=re.search(r'长[*×xX宽]\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*】',s)
    if not ml:ml=re.search(r'【长宽\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)\s*】',s)
    mh=re.search(r'(?:内径|外径)\s*(\d+(?:\.\d+)?)\s*cm\s*高[度]?',s)
    if ml and mh:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh.group(1))),dk_,mat_)
    mh2=re.search(r'高\s*(\d+(?:\.\d+)?)\s*cm\s*】',s)
    if ml and mh2:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh2.group(1))),dk_,mat_)
    mwh=re.search(r'宽\*高\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)',s);ml3=re.search(r'长\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mwh and ml3:return(round(float(ml3.group(1))),round(float(mwh.group(1))),round(float(mwh.group(2))),dk_,mat_)
    mwh5=re.search(r'宽高\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)',s);ml5=re.search(r'长\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mwh5 and ml5:return(round(float(ml5.group(1))),round(float(mwh5.group(1))),round(float(mwh5.group(2))),dk_,mat_)
    mw6=re.search(r'【宽度\s*(\d+(?:\.\d+)?)\s*cm',s);mh6=re.search(r'【高度\s*(\d+(?:\.\d+)?)\s*cm',s);ml6=re.search(r'长\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mw6 and mh6 and ml6:return(round(float(ml6.group(1))),round(float(mw6.group(1))),round(float(mh6.group(1))),dk_,mat_)
    if ml and len(gn(s))>=3:return(round(float(ml.group(1))),round(float(ml.group(2))),round(gn(s)[2]),dk_,mat_)
    return None

def p_zz(s):
    """止合"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s)
    mh=re.search(r'【高度\s*(\d+(?:\.\d+)?)\s*cm',s)
    ml=re.search(r'长x宽【\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mh and ml:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh.group(1))),dk_,mat_)
    mwh=re.search(r'宽\*高【\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)\s*cm',s);ml2=re.search(r'飞机盒长度【\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mwh and ml2:return(round(float(ml2.group(1))),round(float(mwh.group(1))),round(float(mwh.group(2))),dk_,mat_)
    ml3=re.search(r'长\*宽【\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)\s*】\s*mm',s)
    if ml3:return(round(float(ml3.group(1))/10),round(float(ml3.group(2))/10),1,dk_,mat_)
    return None

def p_dy(s):
    """大鱼"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s)
    ml=re.search(r'长宽【\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*cm】?',s)
    mh=re.search(r'(?:高度|高)【?\s*(\d+(?:\.\d+)?)\s*cm】?',s)
    if ml and mh:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh.group(1))),dk_,mat_)
    mh4=re.search(r'高度【\s*(\d+(?:\.\d+)?)\s*cm',s);ml4=re.search(r'长宽【\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*】\s*cm',s)
    if mh4 and ml4:return(round(float(ml4.group(1))),round(float(ml4.group(2))),round(float(mh4.group(1))),dk_,mat_)
    me=re.search(r'长宽(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)',s);he=re.search(r'高(\d+(?:\.\d+)?)【',s)
    if me and he:return(round(float(me.group(1))),round(float(me.group(2))),round(float(he.group(1))),dk_,'EB')
    return None

def p_xxx(s):
    """新鑫星"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s);n=gn(s)
    if len(n)==1 or len(n)==0:return None
    ml=re.search(r'长宽【\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*cm】',s)
    mh=re.search(r'高度【\s*(\d+(?:\.\d+)?)\s*cm',s)
    if ml and mh:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh.group(1))),dk_,mat_)
    mh2=re.search(r'高【\s*(\d+(?:\.\d+)?)\s*厘米',s);ml2=re.search(r'长x宽【\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*】',s)
    if mh2 and ml2:return(round(float(ml2.group(1))),round(float(ml2.group(2))),round(float(mh2.group(1))),dk_,mat_)
    mw=re.search(r'宽\s*(\d+(?:\.\d+)?)\s*cm',s);mh3=re.search(r'高\s*(\d+(?:\.\d+)?)\s*cm',s)
    if mw and mh3:
        l=n[0]if abs(n[0]-float(mw.group(1)))>0.01 else n[-1]
        return(round(l),round(float(mw.group(1))),round(float(mh3.group(1))),dk_,mat_)
    if len(n)>=3:return(round(n[0]),round(n[1]),round(n[2]),dk_,mat_)
    return None

def p_zf(s):
    """正方形"""
    s=s.replace(' ','');dk_=dk(s);mat_=mat(s);n=gn(s)
    if'红'in s or'蓝'in s:return None
    m=re.search(r'高度\s*(\d+(?:\.\d+)?)\s*cm\s*(?:白色|黑色|内径|外径)?\s*\*?\s*(\d+)X(\d+)',s)
    if m:return(round(float(m.group(2))),round(float(m.group(3))),round(float(m.group(1))),dk_,mat_)
    m=re.search(r'高度\s*(\d+(?:\.\d+)?)\s*cm\s*(?:内径|外径)\s*\*?\s*长宽\s*(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)\s*cm',s)
    if m:return(round(float(m.group(2))),round(float(m.group(3))),round(float(m.group(1))),dk_,mat_)
    ml=re.search(r'长宽(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*cm',s);mh=re.search(r'(\d+(?:\.\d+)?)\s*cm\s*(?:内径|外径)',s)
    if ml and mh:return(round(float(ml.group(1))),round(float(ml.group(2))),round(float(mh.group(1))),dk_,mat_)
    ml2=re.search(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*；?\s*(\d+(?:\.\d+)?)\s*cm',s)
    if ml2:return(round(float(ml2.group(1))),round(float(ml2.group(2))),round(float(ml2.group(3))),dk_,mat_)
    ml3=re.search(r'长宽(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)',s);mh3=re.search(r'高\s*(\d+(?:\.\d+)?)\s*cm',s)
    if ml3 and mh3:return(round(float(ml3.group(1))),round(float(ml3.group(2))),round(float(mh3.group(1))),dk_,mat_)
    if len(n)>=3:return(round(n[0]),round(n[1]),round(n[2]),dk_,mat_)
    return None

PARSERS={
    '俊鑫纸品厂':p_jx,'当下家包装':p_dx,
    '深圳市亚润包装材料有限公司':p_yr,'飞机盒止合专卖店':p_zz,
    '深圳市大鱼包装材料有限公司':p_dy,'东莞市新鑫星包装材料有限公司':p_xxx,
    '深圳市正方形纸制品有限公司':p_zf,
}

def p_any(s):
    """通用兜底"""
    s=s.replace(' ','');n=gn(s)
    if len(n)<2:return None
    dk_=dk(s);mat_=mat(s)
    sv=re.sub(r'(\d+)\s*级','0',s)
    lb=re.search(r'长[*×xX宽]\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*】',sv)
    hv=re.search(r'高[度]?\s*[:：]?\[?\s*(\d+(?:\.\d+)?)',sv)
    hv=float(hv.group(1))if hv else None
    if lb and hv:return(round(float(lb.group(1))),round(float(lb.group(2))),round(hv),dk_,mat_)
    wv=re.search(r'宽[度]?\s*[:：]?\s*(\d+(?:\.\d+)?)',sv)
    lv=re.search(r'长[度]?\s*[:：]?\s*(\d+(?:\.\d+)?)',sv)
    if wv and lv and hv:return(round(float(lv.group(1))),round(float(wv.group(1))),round(hv),dk_,mat_)
    lwh3=re.search(r'(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)',sv)
    if lwh3:return(round(float(lwh3.group(1))),round(float(lwh3.group(2))),round(float(lwh3.group(3))),dk_,mat_)
    wh=re.search(r'宽[度]?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:cm|mm)?[\s,;经\-]+\s*(?:高|厚)[度]?\s*[:：]?\s*(\d+(?:\.\d+)?)',sv)
    if wh and lv:return(round(float(lv.group(1))),round(float(wh.group(1))),round(float(wh.group(2))),dk_,mat_)
    if wh:
        for i,v in enumerate(n):
            if abs(v-float(wh.group(1)))>0.01 and abs(v-float(wh.group(2)))>0.01:
                return(round(v),round(float(wh.group(1))),round(float(wh.group(2))),dk_,mat_)
    if len(n)==3:return(round(n[0]),round(n[1]),round(n[2]),dk_,mat_)
    return None

# ===== 主流程 =====
print(f'读源数据...')
df=pd.read_excel(SOURCE,dtype=str,header=None)
data=df.iloc[1:].copy();data.columns=['店','商品id','规格名','规格id'];data['店']=data['店'].str.strip()

to=te=tf=tc=tp=0
for shop_name in sorted([n for n in data['店'].unique() if n!='店铺名称']):
    sd=data[data['店']==shop_name];total=len(sd)
    struct_rules=ALL_R.get(shop_name,{})
    parser=PARSERS.get(shop_name)
    codes=[];no=ne=nc=nf=np=0
    for idx in range(len(sd)):
        row=sd.iloc[idx];pid=str(row['商品id']or'').strip()
        spec=str(row['规格名']or'').strip();sid=str(row['规格id']or'').strip()
        skel=ms(spec);sr=struct_rules.get(skel)
        if sr:
            if sr.get('custom'):codes.append((shop_name,pid,sid,'定制链接'));nc+=1;continue
            # known 结构，尝试兜底
            result=None
            if parser:result=parser(spec)
            if not result:result=p_any(spec)
            if result:
                l,w,h,dk_,mat_=result
                code=f'{l}*{w}*{h}-{dk_}-{mat_}'if mat_!='EB'else f'{l}*{w}*{h}-EB'
                codes.append((shop_name,pid,sid,code));no+=1
            else:codes.append((shop_name,pid,sid,'定制链接'));nf+=1
        else:
            # 未在结构文件中，用解析器
            result=None
            if parser:result=parser(spec)
            if not result:result=p_any(spec)
            if result:
                l,w,h,dk_,mat_=result
                code=f'{l}*{w}*{h}-{dk_}-{mat_}'if mat_!='EB'else f'{l}*{w}*{h}-EB'
                codes.append((shop_name,pid,sid,code));np+=1
            else:codes.append((shop_name,pid,sid,'定制链接'));nf+=1
    
    to+=no;te+=ne;tc+=nc;tf+=nf;tp+=np
    tot=no+ne+nc+nf+np
    safe=shop_name.replace('/','_').replace('\\','_').replace(':','_')
    xls(os.path.join(OUTDIR,f'换绑_{safe}.xlsx'),codes)
    pct=(no+ne+np)/tot*100
    flag=' ✅'if pct==100 else f' ⚠️定制{nc}'
    print(f'{shop_name:25s} {tot:>6d} 结构{no:>5d} EB{ne:>4d} 兜底{np:>5d} 定制{nc:>5d} 失败{nf:>3d}  {pct:>5.1f}%{flag}')

total_all=to+te+tc+tf+tp
print(f'\n总计: {total_all} 结构:{to} 兜底:{tp} EB:{te} 定制:{tc} 失败:{tf}')
print(f'成功率: {(to+te+tp)/total_all*100:.1f}%')
