#!/usr/bin/env python3
import json
with open('/www/wwwroot/feijihe/inventory.json') as f:
    data = json.load(f)
fixed = 0
for d in data['finished']:
    if d['material'] == '国产纸`':
        d['material'] = '国产纸'
        d['name'] = d['name'].replace('国产纸`', '国产纸')
        fixed += 1
    if d['material'] == '' or d['material'] == ' ':
        d['material'] = '国产纸'
        fixed += 1
print(f'修复了 {fixed} 条')
with open('/www/wwwroot/feijihe/inventory.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('已保存')
