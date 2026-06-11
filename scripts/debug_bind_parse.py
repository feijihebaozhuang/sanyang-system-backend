#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试每个用例的解析过程"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

_PRE = r'\s*'
_PST = r'[\s\]】）)\-—＿_]*'
_DIGIT = r'(\d+\.?\d*)'
_UNIT = r'\s*(?:cm|mm|厘米|毫米)?'

LABEL_PATTERNS = [
    ('长', [
        re.compile(r'长[度]?' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
    ('宽', [
        re.compile(r'宽[度]?' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
    ('高', [
        re.compile(r'高[度]?' + _PRE + _DIGIT + _UNIT + _PST),
        re.compile(r'高度' + _PRE + _DIGIT + _UNIT + _PST),
    ]),
]

RE_DIMS_3D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_DIMS_2D = re.compile(r'(\d+\.?\d*)\s*[xX*×]\s*(\d+\.?\d*)')
RE_DIGIT_WITH_UNIT = re.compile(r'(\d+\.?\d*)\s*(cm|mm|厘米|毫米)?', re.IGNORECASE)
RE_QTY = re.compile(r'个')
RE_IGNORE_CTX = re.compile(r'数量|个起订|起订|单个价|单价|元|不含|客服')

def extract_labeled_dims(s):
    dims = {}
    for label, pats in LABEL_PATTERNS:
        for pat in pats:
            m = pat.search(s)
            print(f"    {label} pat={pat.pattern[:60]}... match={m}")
            if m and m.group(1):
                val = float(m.group(1))
                after = s[m.end():m.end()+5]
                if after.startswith('mm') or 'mm' in after[:3]:
                    val = val / 10.0
                seg = s[m.start():m.end()]
                if re.search(r'\d+\.?\d*\s*mm', seg):
                    val = val / 10.0
                dims[label] = val
                print(f"      → val={val}")
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


cases = [
    "（宽）135 mm 外径;【100个】 长度 135 mm;105 mm 双面白",
    "13.5 13.5 10.5   12 13 10  内径 白色",
    "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】",
    "10 10 10   内径  特硬",
    "【双面白色】内径;【36x36 】;10 cm高度（单个价）",
    "36 36 10  内径 白色",
    "【双面白色】外径;【7x7】;10 cm高度（单个价）",
    "7 7 10  外径  白色",
    "【台湾纸】外径;【38x38】;5 cm高度（单个价）",
    "38 38  5   外径  超硬",
]

for idx, text in enumerate(cases):
    print(f"\n{'='*60}")
    print(f"用例 {idx+1}: {text}")
    print(f"{'='*60}")
    
    s = str(text).strip()
    orig = s
    s = s.replace('【',' ').replace('】',' ').replace('（',' ').replace('）',' ')
    s = s.replace('(',' ').replace(')',' ').replace('——',' ')
    s = re.sub(r'[-]{2,}', ' ', s)
    s = re.sub(r'[—＿_]+', ' ', s)
    print(f"标准化后: {s!r}")
    
    print("  extract_labeled_dims:")
    dims = extract_labeled_dims(s)
    print(f"  结果: {dims}")
    
    m3d = RE_DIMS_3D.search(s)
    print(f"  3D (a*b*c): {m3d}")
    if m3d:
        vals = [float(m3d.group(i)) for i in range(1, 4)]
        ctx = s[max(0, m3d.start()-10):m3d.end()+10]
        if 'mm' in ctx:
            vals = [v/10 for v in vals]
        print(f"    vals={vals}")
    
    m2d = RE_DIMS_2D.search(s)
    print(f"  2D (a*b): {m2d}")
    if m2d:
        v1, v2 = float(m2d.group(1)), float(m2d.group(2))
        ctx = s[max(0, m2d.start()-10):m2d.end()+10]
        if 'mm' in ctx:
            v1, v2 = v1/10, v2/10
        print(f"    v1={v1}, v2={v2}")
    
    nums = extract_nums_clean(s)
    print(f"  extract_nums_clean: {nums}")
