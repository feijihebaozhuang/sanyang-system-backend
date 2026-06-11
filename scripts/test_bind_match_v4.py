#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 bind_match_v4 的 parse_spec_v4 能解析哪些规格"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接复制 bind_match_v4.py 中的解析函数来测试
import re

RE_CUSTOM = re.compile(r'定制|定做|定造|订做|订制')
RE_PEARL = re.compile(r'珍珠棉')
RE_BLUE_GREEN = re.compile(r'蓝色|蓝|绿色|绿')
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
RE_INNER = re.compile(r'内径|内尺寸')
RE_OUTER = re.compile(r'外径|外尺寸')

_PRE = r'\s*'
_PST = r'[\s\]】）)\-—＿_]*'
_DIGIT = r'(\d+\.?\d*)'
_UNIT = r'\s*(?:cm|mm|厘米|毫米)?'

LABEL_PATTERNS = [
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

RE_DIMS_3D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_DIMS_2D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_DIGIT_WITH_UNIT = re.compile(r'(\d+\.?\d*)\s*(cm|mm|厘米|毫米)?', re.IGNORECASE)
RE_QTY = re.compile(r'个')
RE_IGNORE_CTX = re.compile(r'数量|个起订|起订|单个价|单价|元|不含|客服')


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

def extract_labeled_dims(s):
    dims = {}
    for label, pats in LABEL_PATTERNS:
        for pat in pats:
            m = pat.search(s)
            if m and m.group(1):
                val = float(m.group(1))
                after = s[m.end():m.end()+5]
                if after.startswith('mm') or 'mm' in after[:3]:
                    val = val / 10.0
                seg = s[m.start():m.end()]
                if re.search(r'\d+\.?\d*\s*mm', seg):
                    val = val / 10.0
                dims[label] = val
                break
    return dims

def extract_nums_clean(s):
    nums = []
    for m in RE_DIGIT_WITH_UNIT.finditer(s):
        val = float(m.group(1))
        unit = (m.group(2) or '').lower()
        if unit in ('mm', '毫米'):
            val = val / 10.0
        if val < 0.5 or val > 500:
            continue
        start = max(0, m.start()-10)
        end = min(len(s), m.end()+10)
        ctx = s[start:end]
        if RE_IGNORE_CTX.search(ctx):
            continue
        if val == int(val) and int(val) >= 10:
            if RE_QTY.search(ctx):
                continue
        nums.append(val)
    return sorted(set(nums), reverse=True)

def parse_spec_v4(text):
    if not text:
        return None
    s = str(text).strip()
    if not s:
        return None
    
    if RE_PEARL.search(s):
        return {'custom': True, 'reason': '珍珠棉'}
    if RE_BLUE_GREEN.search(s):
        return {'custom': True, 'reason': '蓝绿颜色'}
    
    orig = s
    s = s.replace('【',' ').replace('】',' ').replace('（',' ').replace('）',' ')
    s = s.replace('(',' ').replace(')',' ').replace('——',' ')
    s = re.sub(r'[-]{2,}', ' ', s)
    s = re.sub(r'[—＿_]+', ' ', s)
    
    dims = extract_labeled_dims(s)
    
    m = RE_DIMS_3D.search(s)
    if m:
        vals = [float(m.group(i)) for i in range(1, 4)]
        ctx = s[max(0, m.start()-10):m.end()+10]
        if 'mm' in ctx:
            vals = [v/10 for v in vals]
        for lbl, val in zip(['长', '宽', '高'], vals):
            dims.setdefault(lbl, val)
    
    if not (dims.get('长') and dims.get('宽')):
        m = RE_DIMS_2D.search(s)
        if m:
            v1, v2 = float(m.group(1)), float(m.group(2))
            ctx = s[max(0, m.start()-10):m.end()+10]
            if 'mm' in ctx:
                v1, v2 = v1/10, v2/10
            dims.setdefault('长', v1)
            dims.setdefault('宽', v2)
    
    if not (dims.get('长') and dims.get('宽') and dims.get('高')):
        nums = extract_nums_clean(s)
        if len(nums) >= 3:
            if '长' not in dims: dims['长'] = nums[0]
            if '宽' not in dims: dims['宽'] = nums[1]
            if '高' not in dims: dims['高'] = nums[2]
        elif len(nums) == 2:
            if '长' not in dims: dims['长'] = nums[0]
            if '宽' not in dims: dims['宽'] = nums[1]
    
    have_3d = dims.get('长') and dims.get('宽') and dims.get('高')
    have_2d = dims.get('长') and dims.get('宽') and not dims.get('高')
    
    if RE_CUSTOM.search(s) and not have_3d:
        return {'custom': True, 'reason': '定制关键词'}
    if have_2d:
        return None
    if not have_3d:
        return {'custom': True, 'reason': '尺寸不足'}
    
    return {
        '长': dims['长'],
        '宽': dims['宽'],
        '高': dims['高'],
        'dk': guess_dk(s),
        'mat': guess_material(orig),
        'type': '双插盒' if RE_DOUBLE_BOX.search(orig) else ('扣底盒' if RE_BUCKLE_BOX.search(orig) else ''),
    }


test_cases = [
    # === 第1组 ===
    "（宽）135 mm 外径;【100个】 长度 135 mm;105 mm 双面白",
    
    # === 第2组 ===
    "13.5 13.5 10.5   12 13 10  内径 白色",
    
    # === 第3组 ===
    "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】",
    "10 10 10   内径  特硬",
    
    # === 第4组 ===
    "【双面白色】内径;【36x36 】;10 cm高度（单个价）",
    "36 36 10  内径 白色",
    
    # === 第5组 ===
    "【双面白色】外径;【7x7】;10 cm高度（单个价）",
    "7 7 10  外径  白色",
    
    # === 第6组 ===
    "【台湾纸】外径;【38x38】;5 cm高度（单个价）",
    "38 38  5   外径  超硬",
]

print("=" * 80)
print("bind_match_v4.parse_spec_v4 测试")
print("=" * 80)

for i, text in enumerate(test_cases):
    result = parse_spec_v4(text)
    print(f"\n--- 用例 {i+1} ---")
    print(f"原文: {text}")
    if result is None:
        print(f"结果: None (平卡/解析失败)")
    elif result.get('custom'):
        print(f"结果: 定制 (reason={result['reason']})")
    else:
        print(f"  尺寸: 长={result['长']}, 宽={result['宽']}, 高={result['高']}")
        print(f"  内外径: {result['dk']}, 材料: {result['mat']}, 类型: {result.get('type','')}")
