@echo off
chcp 65001 >nul
cd /d "D:\Desktop\sanyang-system\scripts\feishu_cursor"
set FEISHU_DIFY_WORKDIR=D:\Desktop\sanyang-system
node feishu-dify-ws.mjs
pause
