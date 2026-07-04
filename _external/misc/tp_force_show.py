#!/usr/bin/env python3
"""强制显示TP-LINK窗口并截图"""
import pyautogui
import time
import subprocess
from datetime import datetime
import os

os.makedirs("D:\\Desktop\\sanyang-system\\tp_screenshots", exist_ok=True)

# 1. 显示窗口 - 用多种方式尝试
for attempt in range(3):
    print(f"尝试 {attempt+1}: 激活TP-LINK窗口...")
    
    # PowerShell 方式：正常显示窗口
    subprocess.run(['powershell', '-Command', '''
        $h = (Get-Process | Where-Object {$_.MainWindowTitle -like "*TP-LINK*"}).MainWindowHandle
        Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {
                [DllImport("user32.dll")]
                public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                [DllImport("user32.dll")]
                public static extern bool SetForegroundWindow(IntPtr hWnd);
            }
"@
        [Win32]::ShowWindow($h, 9)  # 9 = SW_RESTORE
        Start-Sleep 1
        [Win32]::ShowWindow($h, 1)  # 1 = SW_SHOWNORMAL
        Start-Sleep 1
        [Win32]::SetForegroundWindow($h)
    '''], shell=True)
    time.sleep(3)
    
    # 截图
    screenshot = pyautogui.screenshot()
    path = f"D:\\Desktop\\sanyang-system\\tp_screenshots\\try{attempt+1}_{datetime.now().strftime('%H%M%S')}.png"
    screenshot.save(path)
    print(f"截图已保存: {path}")
    print(f"截图尺寸: {screenshot.size}")
    
    # 找窗口
    windows = list(pyautogui.getAllWindows())
    tp_windows = [w for w in windows if 'TP-LINK' in w.title or '物联' in w.title]
    for w in tp_windows:
        print(f"窗口: {w.title} → left={w.left}, top={w.top}, w={w.width}, h={w.height}, visible={w.visible}")

time.sleep(5)
