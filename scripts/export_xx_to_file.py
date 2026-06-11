# -*- coding: utf-8 -*-
"""阿里新鑫星所有规格导出到txt"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import defaultdict

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

lines = []
lines.append(f'阿里新鑫星: {len(xx_items)}条')
lines.append('')

# 按格式分组
groups = defaultdict(list)
for r in xx_items:
    spec = str(r[2] or '').strip()
    pid = str(r[1] or '').strip()
    spec_id = str(r[3] or '').strip()
    clean = spec.split(';')[0].strip() if ';' in spec else spec
    
    if re.match(r'^\d+[\s]*x\d+[\s]*cm\s*【长x宽】', clean, re.I):
        groups['A: XxY cm 【长x宽】'].append((clean, pid, spec_id, spec))
    elif '外径' in clean and '扣抵盒' in clean:
        groups['B: XxYxZ；外径扣抵盒；材料'].append((clean, pid, spec_id, spec))
    elif '外径白色' in clean:
        groups['C: 外径白色高【Z】；长x宽【XxY】'].append((clean, pid, spec_id, spec))
    elif '长' in clean and ('CM' in clean.upper() or 'cm' in clean) and '宽' in clean:
        groups['D: 长X CM；宽Y cm；高Z cm'].append((clean, pid, spec_id, spec))
    elif re.match(r'^\d+[\s]*(CM|cm)[；;]', clean, re.I):
        groups['D: 长X CM；宽Y cm；高Z cm'].append((clean, pid, spec_id, spec))
    else:
        groups['E: 其他'].append((clean, pid, spec_id, spec))

for gname, items in sorted(groups.items()):
    lines.append(f'\n{"="*60}')
    lines.append(f'{gname}: {len(items)}条')
    lines.append(f'{"="*60}')
    # 去重展示
    seen = {}
    for clean, pid, spec_id, spec in items:
        if clean not in seen:
            seen[clean] = (pid, spec_id, spec)
    for clean in sorted(seen.keys(), key=lambda x: x.lower()):
        pid, spec_id, spec = seen[clean]
        lines.append(f'  {clean}')
        lines.append(f'    商品id={pid[:30]} 规格id={spec_id[:30]}')
    lines.append(f'  共{len(seen)}种不同规格')

# 写文件
txt_path = r'd:\Desktop\新鑫星_全部规格.txt'
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'已导出到: {txt_path}')
print(f'总行数: {len(lines)}')
