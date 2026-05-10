#!/usr/bin/env python3
import subprocess, os, time, sys

os.chdir('/www/wwwroot/feijihe')

# 清理
subprocess.run(['pkill', '-9', '-f', 'gunicorn'], capture_output=True)
subprocess.run(['pkill', '-9', '-f', 'app.py'], capture_output=True)
time.sleep(1)

# 直接启动
gunicorn_path = '/www/wwwroot/feijihe/venv/bin/gunicorn'
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

import urllib.request
try:
    resp = urllib.request.urlopen('http://8.138.10.213:3001/', timeout=5)
    print(f"HTTP: {resp.status}")
except Exception as e:
    print(f"Error: {e}")

print("DONE")
