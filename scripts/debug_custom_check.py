# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import re

s1 = '特硬;双插盒'
s2 = '特硬;扣底盒'

has_dim_format = bool(re.search(r'[\d.]+\s*[xX*×]\s*[\d.]+\s*[xX*×]\s*[\d.]+', s1))
has_cm_dim = bool(re.search(r'【\s*[\d.]+\s*[xX*×]\s*[\d.]+\s*[xX*×]\s*[\d.]+', s1))
has_lwh_keyword = bool(re.search(r'[长宽高][度]*\s*[：:]?\s*【\s*[\d.]+', s1))
print(f's1={repr(s1)}')
print(f'  has_dim_format={has_dim_format}')
print(f'  has_cm_dim={has_cm_dim}')
print(f'  has_lwh_keyword={has_lwh_keyword}')

# 检查数字
nums = re.findall(r'[\d.]+', s1)
print(f'  nums={nums}')
print(f'  len(nums)==0: {len(nums)==0}')

# 检查keywords
keywords = ['定制', '订制', '定做', '加工定制', '不接受退货',
            '咨询客服', '拍下联系客服', '定制产品', '定制拍单',
            '定制尺寸', '万款现货', '联系客服备注', '详情咨询',
            '更多尺寸', '下拉查看', '下拉-', '1000款现模',
            '更多尺寸看详情', '详情-现模', '1000个尺寸']
custom_kw = [kw for kw in keywords if kw in s1]
print(f'  matched_kw={custom_kw}')
print(f'  珍珠棉: {"珍珠棉" in s1}')
