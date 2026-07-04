# Open 助手接 Dify：从 openclaw.json 同步飞书凭证到 .env
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OpenClaw = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"

if (-not (Test-Path $OpenClaw)) {
    Write-Host "未找到 $OpenClaw"
    exit 1
}

$cfg = Get-Content $OpenClaw -Raw | ConvertFrom-Json
$appId = $cfg.channels.feishu.appId
$secret = $cfg.channels.feishu.appSecret

$envPath = Join-Path $Root ".env"
$map = @{
    "FEISHU_DIFY_ENABLED" = "true"
    "FEISHU_APP_ID"       = $appId
    "FEISHU_APP_SECRET"   = $secret
}
$lines = @()
if (Test-Path $envPath) { $lines = @(Get-Content $envPath) }
$out = New-Object System.Collections.Generic.List[string]
$done = @{}
foreach ($l in $lines) {
    if ($l -match '^([A-Z_]+)=(.*)$' -and $map.ContainsKey($Matches[1])) {
        $k = $Matches[1]
        $out.Add("$k=$($map[$k])")
        $done[$k] = $true
    } else {
        $out.Add($l)
    }
}
foreach ($k in $map.Keys) {
    if (-not $done[$k]) { $out.Add("$k=$($map[$k])") }
}
$out | Set-Content $envPath -Encoding utf8

Write-Host "已写入 .env（Open 助手 $appId）"
Write-Host "请把 openclaw.json 里 channels.feishu.enabled 设为 false 并重启 Gateway"
Write-Host "然后运行: .\scripts\start_feishu_dify.ps1"
Write-Host "说明: docs\OPENCLAW_FEISHU_DIFY.md"
Start-Process "https://open.feishu.cn/app/$appId/event"
