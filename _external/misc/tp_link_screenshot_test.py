#!/usr/bin/env python3
"""TP-LINK 安防客户端截图测试"""
import pyautogui
import time
import subprocess
import os
from datetime import datetime

# 1. 激活窗口
result = subprocess.run(
    ['powershell', '-Command', 
     '(Get-Process | Where-Object {$_.MainWindowTitle -like "*TP-LINK*"}) | ForEach-Object { $_.MainWindowTitle }'],
    capture_output=True, text=True
)
print(f"找到的窗口: {result.stdout.strip()}")

if not result.stdout.strip():
    print("未找到TP-LINK窗口，尝试启动...")
    # 尝试启动
    subprocess.run(['start', ''], shell=True)
    time.sleep(5)

# 2. 激活并最大化窗口
subprocess.run(['powershell', '-Command', 
    '(Get-Process | Where-Object {$_.MainWindowTitle -like "*TP-LINK*"}).MainWindowHandle | ForEach-Object { '
    'Add-Type -AssemblyName System.Windows.Forms; '
    '[System.Windows.Forms.SendKeys]::SendWait(\"%{r}\") }'], shell=True)
time.sleep(2)

# 3. 截图
screenshot = pyautogui.screenshot()
path = f"D:\\Desktop\\sanyang-system\\tp_screenshots\\test_{datetime.now().strftime('%H%M%S')}.png"
os.makedirs(os.path.dirname(path), exist_ok=True)
screenshot.save(path)
print(f"截图已保存: {path}")

# 4. 查看截图信息
print(f"截图尺寸: {screenshot.size}")
print(f"文件大小: {os.path.getsize(path)} 字节")

# 尝试用目标窗口区域截图
windows = []
for w in pyautogui.getAllWindows():
    if 'TP-LINK' in w.title or '物联' in w.title:
        windows.append(w)
        print(f"窗口: {w.title} → {w.left},{w.top} {w.width}x{w.height}")

if windows:
    w = windows[0]
    # 移到屏幕内
    w.moveTo(0, 0)
    time.sleep(1)
    w.activate()
    time.sleep(1)
    region_screenshot = pyautogui.screenshot(region=(0, 0, min(w.width, 1920), min(w.height, 1080)))
    region_path = f"D:\\Desktop\\sanyang-system\\tp_screenshots\\test_region_{datetime.now().strftime('%H%M%S')}.png"
    region_screenshot.save(region_path)
    print(f"区域截图已保存: {region_path}")
    print(f"区域截图尺寸: {region_screenshot.size}")
    print(f"区域截图文件大小: {os.path.getsize(region_path)} 字节")
