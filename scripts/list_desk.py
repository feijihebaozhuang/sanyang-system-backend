# -*- coding: utf-8 -*-
import os
for f in sorted(os.listdir(r'D:\Desktop')):
    if f.endswith('.xlsx'):
        print(f'{os.path.getsize(rf"D:\Desktop\{f}"):>10}  {f}')
