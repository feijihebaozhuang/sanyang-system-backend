# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

tests = [
    '高12cm【五层】；长宽【29*21】100个;高12cm【五层】;长宽【29*21】100个',
    '高13cm【五层】；长宽【22*21】100个;高13cm【五层】;长宽【22*21】100个',
    '高12cm【五层】；长宽【29*15】;高12cm【五层】;长宽【29*15】',
    '高12cm【五层】；长宽【29*15】',
]

for s in tests:
    print(f'原文: [{s}]')
    for i, ch in enumerate(s):
        print(f'  [{i}]: U+{ord(ch):04X} ({ch})')
    print()
