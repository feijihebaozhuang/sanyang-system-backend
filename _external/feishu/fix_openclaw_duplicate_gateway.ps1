# 只保留一个 OpenClaw Gateway（19001），结束重复的 18900 等实例
$ErrorActionPreference = "SilentlyContinue"

Write-Host "==> 结束非 19001 的 openclaw gateway 进程..."
Get-CimInstance Win32_Process -Filter "name='node.exe'" | ForEach-Object {
    $cl = $_.CommandLine
    if ($cl -match 'openclaw' -and $cl -match 'gateway' -and $cl -notmatch '19001') {
        Write-Host "  结束 PID $($_.ProcessId): $($cl.Substring(0, [Math]::Min(120, $cl.Length)))..."
        Stop-Process -Id $_.ProcessId -Force
    }
}

Write-Host "==> 确认计划任务（应只启用 OpenClaw Gateway / 19001）..."
schtasks /Query /TN "OpenClaw Gateway" /FO LIST 2>&1 | Select-String "状态|Status|任务名|TaskName"
@("OpenClawGateway", "OpenClaw OpenHelper", "OpenClaw OpenHelper User", "PM2OpenClaw") | ForEach-Object {
    $st = schtasks /Query /TN $_ /FO LIST 2>&1 | Select-String "状态|Status"
    if ($st) { Write-Host "  $_ : $st" }
}

Start-Sleep 2
$left = Get-CimInstance Win32_Process -Filter "name='node.exe'" | Where-Object { $_.CommandLine -match 'openclaw.*gateway' }
if ($left) {
    $left | ForEach-Object { Write-Host "仍在运行: PID $($_.ProcessId)" }
} else {
    Write-Host "无 gateway 进程。执行: openclaw gateway restart"
}
Write-Host "Done. Only OpenClaw Gateway task (port 19001) should run."
