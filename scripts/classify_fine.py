# -*- coding: utf-8 -*-
"""
把所有不同的规格写法模式全部归类，枚举每个子类的样本给你看
"""
import openpyxl, sys, re
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fp = r"d:\Desktop\平台商品.xlsx"
wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
ws = wb['报表1']

patterns = defaultdict(list)

for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    shop, pid, spec_name, spec_id = row
    if not spec_name:
        continue
    s = str(spec_name).strip()
    if i > 200000:  # 前20万行足够覆盖所有模式了
        break
    
    # ---- 识别详细子模式 ----
    label = None
    
    # 有【】的
    if '【' in s:
        has_lwh = ('长' in s or '宽' in s or '高' in s or '厚度' in s or '长度' in s)
        has_x = bool(re.search(r'\d+\.?\d*\s*[xX*×]\s*\d+', s))
        has_bracket_num = bool(re.search(r'【\d+', s))  # 【数量】
        
        if has_lwh:
            # 宽高先、长在后（最常见的）
            if '宽【' in s and '高【' in s and '长【' in s:
                label = '【宽】【高】【长】'
            elif '长【' in s and '宽【' in s and '高【' in s:
                label = '【长】【宽】【高】'
            elif '宽【' in s and '高【' in s and '长度【' in s:
                label = '【宽】【高】【长度】'
            elif '长【' in s:
                label = '有长【】+其他'
            else:
                label = '有【】+长宽高+其他'
        elif '材料' in s or '材质' in s:
            label = '【】+有材料字眼'
        elif has_x:
            # 类似 优质进口纸-黄色【100个】;51*15.6*9.1
            # 判断材料前缀
            prefix = s.split('【')[0].strip()
            if ':' in prefix or '：' in prefix:
                label = '【】+前缀有冒号+x格式尺寸'
            elif '优质' in prefix or '台湾' in prefix or '特硬' in prefix or '超硬' in prefix or '白色' in prefix or '黑色' in prefix:
                label = f'【】+{prefix.split("-")[0] if "-" in prefix else prefix[:6]}...前缀+x格式尺寸'
            else:
                label = '【】+其他前缀+x格式尺寸'
        else:
            label = '【】+无长宽高无x'
    else:
        # 无【】
        has_lwh = ('长' in s or '宽' in s or '高' in s or '厚度' in s or '长度' in s)
        has_x = bool(re.search(r'\d+\.?\d*\s*[xX*×]\s*\d+', s))
        
        if has_lwh:
            # 细分长宽高的顺序和写法
            if '长' in s and '宽' in s and '高' in s:
                if '---' in s or '---' in s:
                    label = '长宽高+---分隔'
                elif '；' in s or ';' in s:
                    label = '长宽高+分号分隔'
                elif ' ' in s:
                    label = '长宽高+空格分隔'
                else:
                    label = '长宽高+其他'
            elif '长' in s and '宽' in s and ('厚' in s):
                label = '长宽厚'
            elif '长x宽x高' in s.lower() or '长*宽*高' in s:
                label = '长x宽x高格式'
            elif has_x:
                label = '有长宽高字眼+有x格式'
            else:
                label = '有长宽高字眼+无x'
        elif has_x:
            label = '纯x格式尺寸(无长宽高字眼)'
        elif re.match(r'^[\d\.\-\sxX*×/]+$', s):
            label = '纯数字符号(无x格式)'
        elif '颜色' in s or '色' in s:
            label = '只有颜色信息'
        else:
            label = '其他无分类'
    
    if len(patterns[label]) < 8:  # 每类最多8个
        patterns[label].append((s, shop))

wb.close()

print("="*80)
print("所有规格写法模式分类（每类最多8个样本）")
print("按出现顺序排列")
print("="*80)

total = sum(len(v) for v in patterns.values())
print(f"\n共 {len(patterns)} 种模式, {total} 个样本")

for label, samples in sorted(patterns.items(), key=lambda x: -len(x[1])):
    print(f"\n--- [{len(samples)}个] {label} ---")
    for s, shop in samples:
        print(f"  {s[:100]}")
