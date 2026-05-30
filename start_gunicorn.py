#!/usr/bin/env python3
"""
旧版启动脚本（已停用 – 原指向 213 服务器）。
213 已下线，实际 service 使用 systemd 直接启动 gunicorn。
此文件保留仅作历史参考。
"""
import subprocess, os, time, sys, urllib.request

os.chdir('/www/feijihe/stable')

# 直接启动
gunicorn_path = '/www/feijihe/stable/venv/bin/gunicorn'
args = [
    gunicorn_path,
    '-w', '2',
    '-b', '0.0.0.0:3001',
    '--timeout', '120',
    'app:app'
]

# 用后台进程方式
p = subprocess.Popen(args, stdout=open('/tmp/gunicorn_out.log','w'), stderr=open('/tmp/gunicorn_err.log','w'))
time.sleep(3)

# 检查
rc = p.poll()
print(f"PID: {p.pid}, returncode: {rc}, alive: {rc is None}")

print("DONE")
