# -*- coding: utf-8 -*-
import os
d = r'D:\Desktop\平台和快麦原始商品'
for f in sorted(os.listdir(d)):
    sz = os.path.getsize(os.path.join(d, f))
    print(f'{sz//1024:>7}KB  {f}')
