# After reboot: WSL Dify + optional Dify-Feishu bridge + remind OpenClaw Gateway
param(
    [switch]$DifyBridge
)

Write-Host "[1] WSL Dify docker + /home/dify fix..."
& (Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "scripts\start_dify.ps1")

if ($DifyBridge) {
    $Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    Set-Location $Root
    $env:MYSQL_PASSWORD = "local-dev"
    $p = Get-NetTCPConnection -LocalPort 5099 -EA SilentlyContinue | Select-Object -First 1
    if ($p) { Stop-Process -Id $p.OwningProcess -Force -EA SilentlyContinue }
    Start-Process python -ArgumentList "scripts/feishu_dify_local.py" -WorkingDirectory $Root -WindowStyle Hidden
    Start-Sleep 2
    $Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $NgrokUrl = "https://gizmo-ardently-nearness.ngrok-free.dev"
    $urlFile = Join-Path $Root "feishu_dify.local.url"
    if (Test-Path $urlFile) {
        $line = (Get-Content $urlFile -Raw).Trim().Split("`n")[0].Trim()
        if ($line -match '^https://') { $NgrokUrl = $line -replace '/api/webhook/feishu$', '' }
    }
    Get-Process ngrok -EA SilentlyContinue | Stop-Process -Force
    Start-Process ngrok -ArgumentList "http","5099","--url=$NgrokUrl" -WindowStyle Hidden
    Write-Host "  Dify bridge :5099 + ngrok started (old app HTTP webhook)"
}

Write-Host "[2] OpenClaw Gateway (仅计划任务 19001，勿双开)..."
$dup = Get-CimInstance Win32_Process -Filter "name='node.exe'" -EA SilentlyContinue |
    Where-Object { $_.CommandLine -match 'openclaw.*gateway' -and $_.CommandLine -notmatch '19001' }
foreach ($p in $dup) { Stop-Process -Id $p.ProcessId -Force -EA SilentlyContinue }
openclaw gateway restart 2>&1 | Out-Null

Write-Host "Done. 飞书=OpenClaw 长连接(19001)。Dify 桥接仅 -DifyBridge 且勿与 OpenClaw 同应用。"
