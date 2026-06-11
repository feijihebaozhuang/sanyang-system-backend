# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# 只跑三羊
with open('rebuild_two_shops_r1.py', 'r', encoding='utf-8') as f:
    code = f.read()
# 跳过小批量
code = code.replace('do_xiaopi()', '# do_xiaopi() skipped')
exec(code)
