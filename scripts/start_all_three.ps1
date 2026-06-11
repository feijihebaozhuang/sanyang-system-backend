# 同时开通三套：OpenClaw + Dify(含飞书桥接) + Cursor飞书（各用各的 App）
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=========================================="
Write-Host " 三套机器人（互不混用）"
Write-Host " OpenClaw  cli_a97ca4949b785cb5  长连接 19001"
Write-Host " Dify      cli_a96c15d3dcf8dbcd  HTTP+ngrok 5099"
Write-Host " Cursor    cli_a96c20180038dbde  长连接 独立黑框"
Write-Host "=========================================="
Write-Host ""

& (Join-Path $Root "scripts\setup_three_bots.ps1")

Write-Host "[A] Dify Docker..."
$shWsl = "/mnt/d/Desktop/sanyang-system/scripts/fix_dify_wsl.sh"
wsl -e bash -lc "sed -i 's/\r$//' '$shWsl' && DIFY_DEEPSEEK_API_KEY='sk-abaf056a56e745b396f0b7937ea503bb' bash '$shWsl'" 2>&1 | Out-Host

Write-Host "[B] OpenClaw Gateway..."
openclaw gateway restart 2>&1 | Out-Host

Write-Host "[C] Dify 飞书桥接 + ngrok（后台）..."
$p5099 = Get-NetTCPConnection -LocalPort 5099 -EA SilentlyContinue | Select-Object -First 1
if ($p5099) { Stop-Process -Id $p5099.OwningProcess -Force -EA SilentlyContinue }
$env:MYSQL_PASSWORD = "local-dev"
Start-Process python -ArgumentList "scripts/feishu_dify_local.py" -WorkingDirectory $Root -WindowStyle Hidden
Start-Sleep 2
$NgrokUrl = "https://gizmo-ardently-nearness.ngrok-free.dev"
$urlFile = Join-Path $Root "feishu_dify.local.url"
if (Test-Path $urlFile) {
    $line = (Get-Content $urlFile -Raw).Trim().Split("`n")[0].Trim()
    if ($line -match '^https://') { $NgrokUrl = $line -replace '/api/webhook/feishu$', '' }
}
Get-Process ngrok -EA SilentlyContinue | Stop-Process -Force
Start-Process ngrok -ArgumentList "http","5099","--url=$NgrokUrl" -WindowStyle Hidden
Start-Sleep 4
try {
    $t = Invoke-RestMethod "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $pub = ($t.tunnels | Where-Object { $_.public_url -match "^https://" } | Select-Object -First 1).public_url
    if ($pub) {
        $wh = "$pub/api/webhook/feishu"
        Write-Host "  Dify 飞书 HTTP 地址（填 cli_a96c15 应用后台）: $wh"
        $wh | Set-Clipboard
    }
} catch { Write-Host "  ngrok 未就绪，请手动: ngrok http 5099" }

Write-Host "[D] Cursor 飞书桥接（新窗口）..."
Start-Process powershell -ArgumentList @(
    "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $Root "scripts\start_feishu_cursor.ps1")
)

Write-Host ""
Write-Host "飞书后台订阅方式:"
Write-Host "  OpenClaw cli_a97ca -> 长连接"
Write-Host "  Dify     cli_a96c15 -> HTTP 服务器 (上面 ngrok 地址)"
Write-Host "  Cursor   cli_a96c2018 -> 长连接"
Write-Host ""
Write-Host "Dify 模型 Key: 设置->DeepSeek-> sk-abaf056a56e745b396f0b7937ea503bb"
