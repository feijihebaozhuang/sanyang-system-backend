# -*- coding: utf-8 -*-
"""
用你的例子测试解析器
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 正则
RE_INNER = re.compile(r'内径|内尺寸')
RE_OUTER = re.compile(r'外径|外尺寸')
RE_CHAOYING = re.compile(r'台湾纸|台湾|超硬')
RE_WHITE = re.compile(r'双面白|双白|白色')
RE_RED = re.compile(r'红色|红')
RE_BLACK = re.compile(r'黑色|黑')
RE_SPECIAL_PRICE = re.compile(r'特价')
RE_NEW_MATERIAL = re.compile(r'新材质|新材')
RE_FIVELAYER = re.compile(r'五层|5层')
RE_THREELAYER = re.compile(r'三层|3层')
RE_DOUBLE_BOX = re.compile(r'双插盒')
RE_BUCKLE_BOX = re.compile(r'扣底盒')
RE_IGNORE_CTX = re.compile(r'数量|个起订|起订|单个价|单价|元|不含|客服')
# 100附近的"个" → 数量标识
RE_QTY = re.compile(r'个')

# 尺寸标签 - 强化版：【】（）() 各种横杠
# 标签前后可以有各种字符
# 长: 长/长度 + 任意分隔符 + 数字 + 单位
# 关键：分隔符可以是 【】（）() —— 等，但不能吃掉紧挨着的数字
# 注意：高4厘米 → 高后面的空格不是必须的
_PRE = r'\s*'     # 标签后到数字前可以是任意空白
_PST = r'[\s\]】）)\-—＿_]*'       # 数字/单位后的字符
_DIGIT = r'(\d+\.?\d*)'
_UNIT = r'\s*(?:cm|mm|厘米|毫米)?'

# 严格版本：标签后直接跟分隔符，然后数字
LABEL_PATS = [
    ('长', [
        re.compile(r'长[度]?' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'长度' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
    ('宽', [
        re.compile(r'宽[度]?' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'宽度' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
    ('高', [
        re.compile(r'高[度]?' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'高度' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'厚[度]?' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'厚度' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
]
RE_3D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_2D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_NUM = re.compile(r'(\d+\.?\d*)\s*(cm|mm|厘米|毫米)?', re.IGNORECASE)

def guess_material(s):
    if RE_CHAOYING.search(s): return '超硬'
    if RE_WHITE.search(s): return '白色'
    if RE_RED.search(s): return '红色'
    if RE_BLACK.search(s): return '黑色'
    if RE_SPECIAL_PRICE.search(s) or RE_NEW_MATERIAL.search(s): return '优质'
    if RE_FIVELAYER.search(s): return 'EB'
    if RE_THREELAYER.search(s): return '3B'
    return '特硬'

def guess_dk(s):
    if RE_INNER.search(s): return '内径'
    if RE_OUTER.search(s): return '外径'
    return '外径'

def extract_labeled(s):
    dims = {}
    for label, pats in LABEL_PATS:
        for pat in pats:
            m = pat.search(s)
            if m and m.group(1):
                val = float(m.group(1))
                # 只检查匹配到的数字后面紧跟的单位
                after = s[m.end():m.end()+5]
                if after.startswith('mm') or after.startswith('mm') or 'mm' in after[:3]:
                    val = val / 10.0
                # 也检查匹配段内（标签和数字之间）是否有mm
                seg = s[m.start():m.end()]
                if re.search(r'\d+\.?\d*\s*mm', seg):
                    val = val / 10.0
                dims[label] = val
                break
    return dims

def extract_nums(s):
    nums = []
    for m in RE_NUM.finditer(s):
        val = float(m.group(1))
        unit = (m.group(2) or '').lower()
        if unit in ('mm','毫米'):
            val = val/10.0
        if val < 0.5 or val > 500: continue
        start = max(0, m.start()-10)
        end = min(len(s), m.end()+10)
        ctx = s[start:end]
        if RE_IGNORE_CTX.search(ctx): continue
        # 如果数字是整数且附近有"个"，可能是数量
        if val == int(val) and int(val) >= 10:
            if RE_QTY.search(ctx): continue
        nums.append(val)
    return sorted(set(nums), reverse=True)

def parse(text):
    if not text: return None
    s = str(text).strip()
    if not s: return None
    
    # 标准化：替换所有括号为空格，便于 regex 匹配
    s = s.replace('【',' ').replace('】',' ').replace('（',' ').replace('）',' ')
    s = s.replace('(',' ').replace(')',' ').replace('——',' ')
    s = re.sub(r'[-]{2,}', ' ', s)
    s = re.sub(r'[—＿_]+', ' ', s)
    
    dims = extract_labeled(s)
    
    m = RE_3D.search(s)
    if m:
        vals = [float(m.group(i)) for i in range(1,4)]
        ctx = s[max(0,m.start()-10):m.end()+10]
        if 'mm' in ctx: vals = [v/10 for v in vals]
        for lbl,val in zip(['长','宽','高'],vals):
            dims.setdefault(lbl, val)
    
    if not (dims.get('长') and dims.get('宽')):
        m = RE_2D.search(s)
        if m:
            v1,v2 = float(m.group(1)), float(m.group(2))
            ctx = s[max(0,m.start()-10):m.end()+10]
            if 'mm' in ctx: v1,v2 = v1/10, v2/10
            dims.setdefault('长', v1)
            dims.setdefault('宽', v2)
    
    if not (dims.get('长') and dims.get('宽') and dims.get('高')):
        nums = extract_nums(s)
        if len(nums) >= 3:
            if '长' not in dims: dims['长'] = nums[0]
            if '宽' not in dims: dims['宽'] = nums[1]
            if '高' not in dims: dims['高'] = nums[2]
        elif len(nums) == 2:
            if '长' not in dims: dims['长'] = nums[0]
            if '宽' not in dims: dims['宽'] = nums[1]
    
    have_3d = dims.get('长') and dims.get('宽') and dims.get('高')
    if not have_3d:
        return None
    
    dk = guess_dk(s)
    mat = guess_material(s)
    
    return {'lwh': f"{dims['长']}*{dims['宽']}*{dims['高']}", 'dk': dk, 'mat': mat}

tests = [
    # (规格名, 期望长, 期望宽, 期望高, 期望内外径, 期望材料)
    ("宽度---100mm【高4厘米】;【数量100个】【长度10厘米】", 10, 10, 4, "外径", "特硬"),
    ("【宽】35 cm  台湾纸;外径【单个价】长度 48 cm;高【10 cm】", 48, 35, 10, "外径", "超硬"),
    ("【宽】30 cm【100个】;外径【双面白】长度 31 cm;【高】3 cm", 31, 30, 3, "外径", "白色"),
    ("【宽】12 cm;外径【单个价】长度  48 cm;【高】3 cm 台湾纸", 48, 12, 3, "外径", "超硬"),
    ("（宽）125 mm 外径;长度 135 mm;105 mm 台湾纸", 13.5, 12.5, 10.5, "外径", "超硬"),
    ("长度 355 mm;（宽）125 mm 外径 台湾纸;【高】105 mm 外径", 35.5, 12.5, 10.5, "外径", "超硬"),
    ("【宽】30 cm;外径【单个价】长度 31 cm;【高】3 cm  台湾纸", 31, 30, 3, "外径", "超硬"),
    ("（宽）125 mm 外径;【100个】  长度 145 mm;105 mm 双面白", 14.5, 12.5, 10.5, "外径", "白色"),
    ("【宽】35 cm  100个;外径【双面白】长度 48 cm;高【10 cm】", 48, 35, 10, "外径", "白色"),
    ("【宽】12 cm;外径【100个】长度  48 cm;【高】3 cm", 48, 12, 3, "外径", "特硬"),
    ("（宽）125 mm 外径;【100个】  长度 145 mm;105 mm", 14.5, 12.5, 10.5, "外径", "特硬"),
    ("【宽】35 cm 外径;外径【100个】长度 48 cm;高【10 cm】", 48, 35, 10, "外径", "特硬"),
    ("【宽】30 cm;外径【100个】长度 31 cm;【高】3 cm", 31, 30, 3, "外径", "特硬"),
    ("长度 355 mm;（宽）125 mm 外径 单个价;【高】105 mm 外径", 35.5, 12.5, 10.5, "外径", "特硬"),
]

print("测试解析结果：\n", flush=True)
ok = 0
fail = 0
for spec, el, ew, eh, edk, emat in tests:
    r = parse(spec)
    status = "✅"
    errs = []
    if r is None:
        status = "❌"
        errs.append("解析失败")
    else:
        lwh = r['lwh']
        parts = lwh.split('*')
        pl, pw, ph = float(parts[0]), float(parts[1]), float(parts[2])
        if abs(pl - el) > 0.01: errs.append(f"长期望{el}得到{pl}")
        if abs(pw - ew) > 0.01: errs.append(f"宽期望{ew}得到{pw}")
        if abs(ph - eh) > 0.01: errs.append(f"高期望{eh}得到{ph}")
        if r['dk'] != edk: errs.append(f"内外径期望{edk}得到{r['dk']}")
        if r['mat'] != emat: errs.append(f"材料期望{emat}得到{r['mat']}")
    
    if errs:
        status = "❌"
        fail += 1
    else:
        ok += 1
    
    lwh_str = r['lwh'] if r else 'None'
    dk_str = r['dk'] if r else 'None'
    mat_str = r['mat'] if r else 'None'
    err_str = '; '.join(errs) if errs else ''
    print(f"{status} {spec[:60]}...", flush=True)
    print(f"   → {lwh_str}-{dk_str}-{mat_str} {err_str}", flush=True)

print(f"\n通过: {ok}/{len(tests)}, 失败: {fail}/{len(tests)}", flush=True)
