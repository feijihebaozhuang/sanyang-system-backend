# 一键配置：飞书 <-> Cursor Agent CLI（长连接 WebSocket）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\setup_feishu_cursor.ps1
param(
    [switch]$SkipLogin,
    [switch]$SkipTask,
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bridge = Join-Path $Root "scripts\feishu_cursor"
$CfgDir = Join-Path $env:USERPROFILE ".config\feishu-agent-bridge"
$CfgFile = Join-Path $CfgDir "feishu.json"
$Desktop = [Environment]::GetFolderPath("Desktop")
$TaskName = "SanyangFeishuCursor"

function Write-Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }

Write-Host "Feishu <-> Cursor bridge setup" -ForegroundColor Green
Write-Host "Workspace: $Root"

Write-Step "Check feishu.json"
if (-not (Test-Path $CfgFile)) {
    New-Item -ItemType Directory -Force -Path $CfgDir | Out-Null
    $template = @{
        appId     = "cli_YOUR_APP_ID"
        appSecret = "YOUR_APP_SECRET"
        timeout   = 300000
        directory = ($Root -replace '\\', '/')
        logLevel  = "info"
    }
    $template | ConvertTo-Json | Set-Content $CfgFile -Encoding UTF8
    Write-Host "Template created. Edit appId/appSecret then re-run." -ForegroundColor Yellow
    Start-Process "https://open.feishu.cn/app"
    exit 1
}

$cfg = Get-Content $CfgFile -Raw | ConvertFrom-Json
if ($cfg.appId -match "YOUR_APP_ID" -or -not $cfg.appSecret) {
    Write-Host "feishu.json still has placeholder values." -ForegroundColor Red
    exit 1
}

try {
    $body = @{ app_id = $cfg.appId; app_secret = $cfg.appSecret } | ConvertTo-Json
    $tok = Invoke-RestMethod -Uri "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" `
        -Method POST -Body $body -ContentType "application/json"
    if ($tok.code -ne 0) { throw $tok.msg }
    Write-Host "Feishu credentials OK" -ForegroundColor Green
} catch {
    Write-Host "Feishu credential check failed: $_" -ForegroundColor Red
    exit 1
}

Write-Step "Check Cursor Agent CLI"
$agentCmd = Join-Path $env:LOCALAPPDATA "cursor-agent\agent.cmd"
if (-not (Test-Path $agentCmd)) {
    Write-Host "Installing agent CLI..."
    irm 'https://cursor.com/install?win32=true' | iex
}

$agentStatus = & agent status 2>&1 | Out-String
if ($agentStatus -match 'Not logged in') {
    Write-Host "Agent NOT logged in yet." -ForegroundColor Yellow
    if (-not $SkipLogin) {
        Write-Host "Opening browser for agent login..."
        Start-Process "agent" -ArgumentList "login" -Wait:$false
        Read-Host "Complete login in browser, then press Enter"
        $agentStatus = & agent status 2>&1 | Out-String
    }
}
if ($agentStatus -notmatch 'Not logged in') {
    Write-Host "Agent logged in OK" -ForegroundColor Green
} else {
    Write-Host "Agent still not logged in - use desktop shortcut later" -ForegroundColor Yellow
}

Write-Step "npm install"
Set-Location $Bridge
if (-not (Test-Path "node_modules")) {
    npm install 2>&1 | Out-Host
} else {
    Write-Host "node_modules exists, skip"
}

Write-Step "Desktop shortcuts"
$loginBat = Join-Path $Desktop "Login Cursor Agent.bat"
$startBat = Join-Path $Desktop "Start Feishu-Cursor.bat"
@(
    '@echo off',
    'chcp 65001 >nul',
    'title Login Cursor Agent',
    'echo Open browser and login with Cursor account...',
    'agent login',
    'echo.',
    'agent status',
    'pause'
) | Set-Content $loginBat -Encoding UTF8

@(
    '@echo off',
    'chcp 65001 >nul',
    'title Feishu-Cursor bridge',
    "cd /d `"$Root`"",
    'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start_feishu_cursor.ps1"',
    'pause'
) | Set-Content $startBat -Encoding UTF8

# Keep Chinese name bat for existing habit
$startBatCn = Join-Path $Desktop "启动 Cursor飞书.bat"
Copy-Item $startBat $startBatCn -Force
Write-Host "  $loginBat"
Write-Host "  $startBatCn"

if (-not $SkipTask) {
    Write-Step "Scheduled task: $TaskName"
    $startPs1 = Join-Path $Root "scripts\start_feishu_cursor.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startPs1`" -Background"
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Settings $settings -Force | Out-Null
    Write-Host "Autostart registered at Windows logon" -ForegroundColor Green
}

Write-Step "Feishu console checklist"
Write-Host "  App: $($cfg.appId)"
Write-Host "  URL: https://open.feishu.cn/app/$($cfg.appId)/event"
Write-Host "  Mode: long-connection (WebSocket), NOT HTTP"
Write-Host "  Event: im.message.receive_v1"

if ($StartNow -or -not $SkipTask) {
    Write-Step "Start bridge"
    & (Join-Path $Root "scripts\start_feishu_cursor.ps1") -Background
    Start-Sleep -Seconds 3
    $log = Join-Path $Root "feishu_cursor.log"
    if (Test-Path $log) {
        Write-Host "--- tail log ---"
        Get-Content $log -Tail 8 -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Done. Send 'test' to Feishu bot." -ForegroundColor Green
Write-Host "Log: $Root\feishu_cursor.log"
