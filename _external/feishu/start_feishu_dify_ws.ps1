# 启动 Dify 飞书长连接桥接（WebSocket，无需 ngrok）
param(
    [switch]$Background,
    [switch]$KeepHttp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bridge = Join-Path $Root "scripts\feishu_cursor"
$LogFile = Join-Path $Root "feishu_dify_ws.log"
$ErrFile = Join-Path $Root "feishu_dify_ws.err.log"
$PidFile = Join-Path $Bridge "feishu-dify-ws.pid"

# 停旧进程
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'feishu-dify-ws\.mjs' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid -match '^\d+$') {
        Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

# 如果不保留 HTTP，停掉旧的 HTTP 桥接 + ngrok
if (-not $KeepHttp) {
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-NetTCPConnection -LocalPort 5099 -ErrorAction SilentlyContinue |
        Select-Object -First 1 | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}

$env:FEISHU_DIFY_WORKDIR = $Root

$server = Join-Path $Bridge "feishu-dify-ws.mjs"

# 先用 -NoProfile 直接启动一个独立的 node 进程，避免被 PowerShell 宿主进程影响
if ($Background) {
    $env:FEISHU_DIFY_AUTOSTART = "1"
    $nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
    if (-not $nodeExe) { $nodeExe = "node" }
    # 用 Start-Process 启动独立进程，不重定向输出（避免管道阻塞导致进程退出）
    $proc = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -WindowStyle Hidden -Command `"& '$nodeExe' '$server' 2>&1 | Out-Null`"" -WorkingDirectory $Bridge -PassThru -WindowStyle Hidden
    $proc.Id | Set-Content $PidFile -Encoding ASCII
    Write-Host "Started Feishu-Dify WS bridge in background, PID=$($proc.Id)"
} else {
    Write-Host "启动 Dify 飞书长连接桥接（前台）..."
    Write-Host "日志: $LogFile"
    Write-Host ""
    Set-Location $Bridge
    node "feishu-dify-ws.mjs" 2>&1 | Tee-Object -FilePath $LogFile -Append
}
