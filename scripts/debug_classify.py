# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pids_test = ['5145118190894', '5145118190893', '4863776885263', '4772764692890', '4768923641932']
specs_test = [
    '白色【100个】宽度 10 CM;长 11 *宽 ? * 高 6 【所量即所装=内径】',
    '宽度 10 CM 特硬-牛皮色【100个】;长 11 *宽 ? * 高 6 【所量即所装=内径】',
    '白色【内径】100个;10x10x2 cm',
    '黑色【内尺寸】【100个】;10x10x2 cm',
    '进口牛皮色【内尺寸】;10x10x2 cm',
]

def is_waijing(s):
    if '内径' in s or '内尺寸' in s:
        if '外径' in s or '外尺寸' in s:
            return True
        return False
    return True

def make_skeleton(s):
    s = re.sub(r'\d+\.?\d*', 'N', s)
    s = re.sub(r'\s+', '', s)
    return s[:300]

# 看这些spec的骨架是否匹配5-剩余商品结构.txt
with open(r'D:\Desktop\5-剩余商品结构.txt', 'r', encoding='utf-8') as f:
    remain_content = f.read()

for i, spec in enumerate(specs_test):
    sk = make_skeleton(spec)
    waijing = is_waijing(spec)
    result = '外径' if waijing else '内径'
    
    # 看骨架是否在剩余结构中
    found = f'  剩余结构匹配: {sk in remain_content}'
    
    print(f'pid={pids_test[i]}')
    print(f'  骨架: {sk}')
    print(f'  is_waijing结果: {result}')
    print(f'  {found}')
