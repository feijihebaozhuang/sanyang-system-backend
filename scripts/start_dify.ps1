# 启动并修复 WSL 本机 Dify（不启动飞书桥接，避免与 OpenClaw 抢同一应用）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$sh = Join-Path $Root "scripts\fix_dify_wsl.sh"
# D:\Desktop\... -> /mnt/d/Desktop/...
if ($sh -match '^([A-Z]):(.*)$') {
    $shWsl = ('/mnt/{0}{1}' -f $Matches[1].ToLower(), ($Matches[2] -replace '\\','/'))
}

if (Test-Path "$Root\.env") {
    $key = (Get-Content "$Root\.env" | Where-Object { $_ -match '^DIFY_API_KEY=' }) -replace '^DIFY_API_KEY=',''
    if ($key) { $env:DIFY_API_KEY = $key.Trim() }
}

Write-Host "==> Dify docker + health fix (WSL)..."
wsl -e bash -lc "chmod +x '$shWsl' && DIFY_API_KEY='${env:DIFY_API_KEY}' bash '$shWsl'"

Write-Host ""
Write-Host "Dify 控制台: http://localhost"
Write-Host "API 基址:    http://127.0.0.1/v1"
Write-Host ""
Write-Host "飞书接 Dify 需单独应用 + ngrok，见 docs/FEISHU_DIFY.md"
Write-Host "  .\scripts\start_feishu_dify.ps1   （勿与 OpenClaw 同一 cli_ 应用同时开）"
