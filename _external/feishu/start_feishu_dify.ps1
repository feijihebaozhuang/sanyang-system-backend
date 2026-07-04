# 一键启动：本机飞书↔Dify 桥接 + ngrok
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".env")) {
    Write-Host "缺少 .env，请先运行: python scripts/setup_feishu_dify_local.py"
    exit 1
}

# 释放端口
foreach ($port in 5099) {
    $c = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) {
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

$env:MYSQL_PASSWORD = if ($env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD } else { "local-dev" }

Write-Host "[1/3] 启动桥接服务 :5099 ..."
$bridge = Start-Process -FilePath "python" -ArgumentList "scripts/feishu_dify_local.py" -WorkingDirectory $Root -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:5099/" -TimeoutSec 5
    Write-Host "  enabled=$($r.enabled) dify=$($r.dify_api_base)"
} catch {
    Write-Host "  桥接未就绪: $_"
}

$NgrokUrl = "https://gizmo-ardently-nearness.ngrok-free.dev"
$urlFile = Join-Path $Root "feishu_dify.local.url"
if (Test-Path $urlFile) {
    $line = (Get-Content $urlFile -Raw).Trim().Split("`n")[0].Trim()
    if ($line -match '^https://') { $NgrokUrl = $line -replace '/api/webhook/feishu$', '' }
}
Write-Host "[2/3] 启动 ngrok（固定域名，飞书后台填一次即可）..."
Write-Host "  $NgrokUrl"
$ng = Get-Process ngrok -ErrorAction SilentlyContinue
if ($ng) { $ng | Stop-Process -Force }
Start-Process -FilePath "ngrok" -ArgumentList "http","5099","--url=$NgrokUrl" -WindowStyle Hidden
Start-Sleep -Seconds 4

$pub = $null
try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $pub = ($tunnels.tunnels | Where-Object { $_.public_url -match "^https://" } | Select-Object -First 1).public_url
} catch {
    $pub = $null
}

if ($pub) {
    $wh = "$pub/api/webhook/feishu"
    Write-Host "[3/3] Feishu webhook URL (paste in open.feishu.cn event subscription):"
    Write-Host "  $wh"
    $wh | Set-Clipboard
    Write-Host "  已复制到剪贴板"
} else {
    Write-Host "[3/3] ngrok 未就绪，请手动运行: ngrok http 5099"
}

Write-Host ""
Write-Host "Dify 控制台: http://localhost （应用 Feishu Bot 需已发布且配置模型）"
Write-Host "停止: Stop-Process -Id $($bridge.Id) -Force; Get-Process ngrok -EA 0 | Stop-Process -Force"
Write-Host "桥接 PID: $($bridge.Id)"
