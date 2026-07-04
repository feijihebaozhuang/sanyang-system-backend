# 重启飞书-Cursor 桥接（后台 Agent 模式）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bridge = Join-Path $Root "scripts\feishu_cursor"
$LogFile = Join-Path $Root "feishu_cursor.log"
$ErrFile = Join-Path $Root "feishu_cursor.err.log"
$PidFile = Join-Path $Bridge "bridge.pid"

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'server\.mjs' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid -match '^\d+$') {
        Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

$env:FEISHU_TRANSPORT = "ws"
$env:FEISHU_CURSOR_WORKDIR = $Root
Remove-Item Env:FEISHU_CURSOR_MODE -ErrorAction SilentlyContinue

$nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $nodeExe) { $nodeExe = "node" }

$server = Join-Path $Bridge "server.mjs"
$proc = Start-Process -FilePath $nodeExe -ArgumentList "`"$server`"" -WorkingDirectory $Bridge `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $LogFile -RedirectStandardError $ErrFile
$proc.Id | Set-Content $PidFile -Encoding ASCII
Write-Host "Restarted Feishu-Cursor bridge, PID=$($proc.Id), mode=default (full agent)"
