# 本机只保留：计划任务 OpenClaw Gateway (19001) + 飞书长连接，禁用其它 OpenClaw 自启动
# 用法（管理员 PowerShell）： .\scripts\setup_single_openclaw_feishu.ps1

$ErrorActionPreference = "Stop"
$tasksDisable = @(
    "OpenClawGateway",
    "OpenClaw OpenHelper",
    "OpenClaw OpenHelper User",
    "PM2OpenClaw"
)
foreach ($t in $tasksDisable) {
    schtasks /Change /TN $t /DISABLE 2>&1 | Out-Null
    Write-Host "[禁用计划任务] $t"
}
schtasks /Change /TN "OpenClaw Gateway" /ENABLE 2>&1 | Out-Null
Write-Host "[启用] OpenClaw Gateway -> gateway.cmd :19001"

$desktop = @(
    "$env:USERPROFILE\Desktop\start_openclaw.bat",
    "$env:USERPROFILE\Desktop\start_openclaw.vbs"
)
foreach ($f in $desktop) {
    if (Test-Path $f) {
        Remove-Item $f -Force
        Write-Host "[删除] $f"
    }
}

& "$PSScriptRoot\fix_openclaw_duplicate_gateway.ps1"

$cfg = "$env:USERPROFILE\.openclaw\openclaw.json"
if (Test-Path $cfg) {
    $j = Get-Content $cfg -Raw | ConvertFrom-Json
    if (-not $j.channels) { $j | Add-Member NotePropertyName channels -NotePropertyValue (@{}) }
    if (-not $j.channels.feishu) { $j.channels | Add-Member NotePropertyName feishu -NotePropertyValue (@{}) }
    $j.channels.feishu | Add-Member NotePropertyName enabled -NotePropertyValue $true -Force
    $j.channels.feishu | Add-Member NotePropertyName connectionMode -NotePropertyValue "websocket" -Force
    $j | ConvertTo-Json -Depth 12 | Set-Content $cfg -Encoding UTF8
    Write-Host "[配置] 飞书通道 enabled=true, websocket"
}

openclaw gateway restart 2>&1 | Out-Host
Write-Host ""
Write-Host "完成。开机仅「OpenClaw Gateway」黑框(19001)；飞书勿再配 Dify/ngrok 同一应用。"
