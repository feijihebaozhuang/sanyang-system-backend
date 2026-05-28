# 飞书 <-> Cursor Agent 桥接（长连接 WebSocket）
param(
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bridge = Join-Path $Root "scripts\feishu_cursor"
$LogFile = Join-Path $Root "feishu_cursor.log"
$ErrFile = Join-Path $Root "feishu_cursor.err.log"
$CfgFile = Join-Path $env:USERPROFILE ".config\feishu-agent-bridge\feishu.json"

if (-not (Test-Path $CfgFile)) {
    Write-Host "缺少 $CfgFile — 请先运行: scripts\setup_feishu_cursor.ps1"
    exit 1
}

# 清理所有 server.mjs（避免 orphan 占长连接）
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'server\.mjs' } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1

$bridgePidFile = Join-Path $Bridge "bridge.pid"
if (Test-Path $bridgePidFile) {
    $oldPid = Get-Content $bridgePidFile -ErrorAction SilentlyContinue
    if ($oldPid -match '^\d+$') {
        Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
    }
}

$bridgeServer = Join-Path $Bridge "server.mjs"

Set-Location $Bridge
if (-not (Test-Path "node_modules")) {
    Write-Host "首次安装 feishu-agent-bridge..."
    npm install 2>&1 | Out-Host
}

$env:FEISHU_TRANSPORT = "ws"
$env:FEISHU_CURSOR_WORKDIR = $Root

$agentCmd = Join-Path $env:LOCALAPPDATA "cursor-agent\agent.cmd"
if (-not (Test-Path $agentCmd)) {
    Write-Host "未检测到 Cursor Agent CLI，正在安装..."
    irm 'https://cursor.com/install?win32=true' | iex
}

$agentStatus = & agent status 2>&1 | Out-String
if ($agentStatus -match 'Not logged in') {
    Write-Host ""
    Write-Host "【警告】Cursor Agent 尚未登录 — 飞书能收到消息但 AI 会失败。" -ForegroundColor Yellow
    Write-Host "请运行: agent login  或双击桌面「登录 Cursor Agent.bat」"
    Write-Host ""
    if (-not $Background -and -not $env:FEISHU_CURSOR_AUTOSTART) {
        $ans = Read-Host "仍要启动桥接? (y/N)"
        if ($ans -notmatch '^[yY]') { exit 1 }
    }
} else {
    Write-Host "Cursor Agent 已登录 ✓"
}

Write-Host "启动飞书-Cursor 长连接..."
Write-Host "工作区: $Root"
Write-Host "日志: $LogFile"

if ($Background) {
    $env:FEISHU_CURSOR_AUTOSTART = "1"
    $nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
    if (-not $nodeExe) { $nodeExe = "node" }
    $proc = Start-Process -FilePath $nodeExe -ArgumentList "`"$bridgeServer`"" -WorkingDirectory $Bridge `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError $ErrFile
    $proc.Id | Set-Content $bridgePidFile -Encoding ASCII
    Write-Host ("Started in background, process " + $proc.Id)
} else {
    Write-Host "飞书后台: 事件订阅 -> 使用长连接（勿填 HTTP 地址）"
    Write-Host ""
    node server.mjs 2>&1 | Tee-Object -FilePath $LogFile -Append
}
