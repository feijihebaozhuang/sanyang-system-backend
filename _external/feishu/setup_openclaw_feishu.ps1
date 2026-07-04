# 用新的飞书应用资料配置 OpenClaw 飞书通道（长连接，与 Dify 桥接二选一）
param(
    [Parameter(Mandatory = $true)][string]$AppId,
    [Parameter(Mandatory = $true)][string]$AppSecret,
    [string]$VerificationToken = "",
    [string]$EncryptKey = "",
    [string]$ConnectionMode = "websocket"
)

$OpenClaw = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"
if (-not (Test-Path $OpenClaw)) {
    Write-Host "未找到 $OpenClaw"
    exit 1
}

$cfg = Get-Content $OpenClaw -Raw | ConvertFrom-Json
if (-not $cfg.channels) { $cfg | Add-Member -NotePropertyName channels -NotePropertyValue (@{}) }
if (-not $cfg.channels.feishu) { $cfg.channels | Add-Member -NotePropertyName feishu -NotePropertyValue (@{}) }

$cfg.channels.feishu.enabled = $true
$cfg.channels.feishu.appId = $AppId
$cfg.channels.feishu.appSecret = $AppSecret
$cfg.channels.feishu.connectionMode = $ConnectionMode
if ($VerificationToken) { $cfg.channels.feishu.verificationToken = $VerificationToken }
if ($EncryptKey) { $cfg.channels.feishu.encryptKey = $EncryptKey }

if (-not $cfg.plugins.entries.feishu) {
    $cfg.plugins.entries | Add-Member -NotePropertyName feishu -NotePropertyValue (@{ enabled = $true })
} else {
    $cfg.plugins.entries.feishu.enabled = $true
}

$cfg | ConvertTo-Json -Depth 20 | Set-Content $OpenClaw -Encoding utf8

Write-Host "已写入 openclaw.json（App $AppId, 模式 $ConnectionMode）"
Write-Host ""
Write-Host "飞书后台请配置："
Write-Host "  事件订阅 -> 使用长连接接收事件 (websocket)"
Write-Host "  或 webhook 模式时填 Verification Token / Encrypt Key"
Write-Host ""
Write-Host "与 Dify 桥接不能同时收同一应用的消息："
Write-Host "  - 用 OpenClaw：关闭 start_feishu_dify.ps1，飞书勿填 ngrok HTTP 地址"
Write-Host "  - 用 Dify 桥接：openclaw channels.feishu.enabled = false"
Write-Host ""
Write-Host "请重启 OpenClaw Gateway 后在飞书里测试机器人。"
Start-Process "https://open.feishu.cn/app/$AppId/event"
