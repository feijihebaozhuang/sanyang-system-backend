# -*- coding: utf-8 -*-
import os, subprocess

cmds = '''
git add scripts/batch_zh_v4.py scripts/merge_batch_40_41.py scripts/reset_and_run.py scripts/verify_zh.py scripts/restore_nm.py scripts/check_zh_lost.py scripts/check_zh_result.py scripts/debug_zh_re.py scripts/debug_char.py scripts/find_zh_in_nm.py scripts/show_zh_nm.py scripts/check_zh_left.py scripts/show_unrec.py scripts/check_ok_batches.py scripts/show_batch_41.py
git commit -m "处理天猫止合: 1119条全部解析成功(6种格式), 16条快麦匹配输出到第41批"
git push
'''

for cmd in cmds.strip().split('\n'):
    cmd = cmd.strip()
    if not cmd: continue
    print(f'> {cmd}')
    r = subprocess.run(cmd, shell=True, cwd=r'D:\Desktop\sanyang-system', capture_output=True, text=True)
    if r.stdout: print(r.stdout)
    if r.stderr: print(r.stderr)
    if r.returncode != 0:
        print(f'!!! 失败 rc={r.returncode}')
        break
