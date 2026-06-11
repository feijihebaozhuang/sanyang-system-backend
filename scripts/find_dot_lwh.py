# -*- coding: utf-8 -*-
"""
从平台商品.xlsx的规格名称中，精准找出长宽高为小数的商品
排除长宽高三项同时为.5的
输出到桌面
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)

# ===== 精准提取长宽高 =====
def extract_lwh(s):
    """从规格名称中精准提取长宽高"""
    s = str(s)
    
    # 优先从【】里提取，寻找常见模式
    patterns = [
        # 外尺寸【LxWxH】或【L*W*H】
        r'外[尺寸]*寸*[大小]*[：:]?\s*【\s*([\d.]+)\s*[xX*]\s*([\d.]+)\s*[xX*]\s*([\d.]+)\s*cm*\s*】',
        # 【长L宽W高H】或【长Lx宽Wx高H】
        r'【\s*长\s*([\d.]+)\s*[xX*×]\s*宽\s*([\d.]+)\s*[xX*×]\s*高\s*([\d.]+)\s*】',
        # 长【L】宽【W】高【H】
        r'长[度]*[：:]?\s*【\s*([\d.]+)\s*cm*\s*】.*?宽[度]*[：:]?\s*【\s*([\d.]+)\s*cm*\s*】.*?高[度]*[：:]?\s*【\s*([\d.]+)\s*cm*\s*】',
        # L*W*H cm 或 LxWxH cm（外尺寸标注附近）
        r'(?:外尺寸|外径|外寸)[^；;]*?【\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*】',
        # L*W*H 前面有长度/宽度/高度上下文
        r'(?:长|长度)[：:]?\s*([\d.]+)\s*cm*\s*(?:宽|宽度)[：:]?\s*([\d.]+)\s*cm*\s*(?:高|高度)[：:]?\s*([\d.]+)\s*cm*',
        # 规格名直接以数字开头 LxWxH 并且后面有cm或材料等
        r'^\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*(?:cm|mm|C)?',
        # 中间有 LxWxH
        r'(?:^|[；;，,\s])+\s*([\d.]+)\s*[xX*]\s*([\d.]+)\s*[xX*]\s*([\d.]+)\s*(?:cm|mm|C)?(?:\s|$|【|；|;|,)',
    ]
    
    for pat in patterns:
        m = re.search(pat, s, re.I | re.S)
        if m:
            try:
                l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
                # 排除明显不是长宽高的数字（比如数量）
                if 0 < l <= 200 and 0 < w <= 200 and 0 < h <= 200:
                    return (l, w, h)
            except: pass
    
    # 最后尝试：找连续的 LxWxH 或 L*W*H 格式（中间没有中文）
    m = re.search(r'(?<![\d.])([\d.]+)\s*[xX*]\s*([\d.]+)\s*[xX*]\s*([\d.]+)(?:\s*cm|\s*mm|\s*C)?(?![\d.])', s)
    if m:
        try:
            l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if 0 < l <= 200 and 0 < w <= 200 and 0 < h <= 200:
                return (l, w, h)
        except: pass
    
    return None

def is_dot5(v):
    """判断是否为x.5"""
    return v != int(v) and v * 2 == int(v * 2)

results = []
total = len(df)
for idx, (_, row) in enumerate(df.iterrows()):
    s = str(row.get('平台规格名称', '')).strip()
    if not s: continue
    
    lwh = extract_lwh(s)
    if not lwh: continue
    
    l, w, h = lwh
    has_dot = any(n != int(n) for n in (l, w, h))
    if not has_dot: continue  # 排除全是整数的
    
    # 是否三项同时为.5
    all_dot5 = all(is_dot5(n) for n in (l, w, h))
    if all_dot5: continue  # 排除
    
    shop = str(row.get('店铺名称', '')).strip()
    pid = str(row.get('平台商品id', '')).strip()
    sid = str(row.get('平台规格id', '')).strip()
    results.append((shop, pid, s, l, w, h))

print(f'总行: {total}')
print(f'找到长宽高含小数且不全为.5: {len(results)} 条')

# 输出到桌面
out = r'D:\Desktop\长宽高含小数商品.xlsx'
pd.DataFrame(results, columns=['店铺名称', '平台商品id', '规格名称', '长', '宽', '高']).to_excel(out, index=False)

import openpyxl
wb = openpyxl.load_workbook(out)
ws = wb.active
ws.insert_rows(1)
ws.cell(1, 2).value = '长宽高含小数的商品（已排除三项全.5）'
ws.column_dimensions['C'].width = 60
wb.save(out)

print(f'✅ 已输出到: {out}')
print(f'共 {len(results)} 条')
