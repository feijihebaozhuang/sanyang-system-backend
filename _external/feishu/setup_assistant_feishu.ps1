# Configure OpenClaw: Feishu app + OpenClaw 用的 DeepSeek key（Dify 的 sk 请在 Dify 控制台填）
param(
    [Parameter(Mandatory = $true)][string]$AppId,
    [Parameter(Mandatory = $true)][string]$AppSecret,
    [Parameter(Mandatory = $true)][string]$DeepSeekKey
)

$ErrorActionPreference = "Stop"

$auth = Join-Path $env:USERPROFILE ".openclaw\agents\main\agent\auth-profiles.json"
@{
    deepseek = @{
        baseUrl = "https://api.deepseek.com/v1"
        apiKey  = $DeepSeekKey
    }
} | ConvertTo-Json | Set-Content $auth -Encoding UTF8
Write-Host "[OK] DeepSeek key -> auth-profiles.json"

$cfgPath = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"
$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
if (-not $cfg.channels) { $cfg | Add-Member NotePropertyName channels -NotePropertyValue (@{}) }
if (-not $cfg.channels.feishu) { $cfg.channels | Add-Member NotePropertyName feishu -NotePropertyValue (@{}) }

$cfg.channels.feishu.enabled = $true
$cfg.channels.feishu.appId = $AppId
$cfg.channels.feishu.appSecret = $AppSecret
$cfg.channels.feishu.connectionMode = "websocket"
$cfg.channels.feishu.dmPolicy = "open"
$cfg.channels.feishu.groupPolicy = "open"
$cfg.channels.feishu.requireMention = $false

if (-not $cfg.plugins.entries.feishu) {
    $cfg.plugins.entries | Add-Member NotePropertyName feishu -NotePropertyValue (@{ enabled = $true })
} else {
    $cfg.plugins.entries.feishu.enabled = $true
}
if (-not $cfg.plugins.allow) {
    $cfg.plugins | Add-Member NotePropertyName allow -NotePropertyValue @("feishu", "deepseek", "memory-core") -Force
}

if (-not $cfg.agents.defaults.model) {
    $cfg.agents.defaults | Add-Member NotePropertyName model -NotePropertyValue (@{ primary = "deepseek/deepseek-v4-flash" })
} else {
    $cfg.agents.defaults.model.primary = "deepseek/deepseek-v4-flash"
}
$cfg.agents.defaults.thinkingDefault = "off"
$cfg.agents.defaults.bootstrapMaxChars = 4000
$cfg.agents.defaults.bootstrapTotalMaxChars = 20000

$cfg | ConvertTo-Json -Depth 12 | Set-Content $cfgPath -Encoding UTF8
Write-Host "[OK] openclaw.json Feishu AppId=$AppId dmPolicy=open"

Write-Host ""
Write-Host "Feishu console: https://open.feishu.cn/app/$AppId/event"
Write-Host "  Event: use long-connection (websocket)"
Write-Host "  Permissions: im:message, im:message:send_as_bot"
Write-Host "  Publish app and add bot to chat"
Start-Process "https://open.feishu.cn/app/$AppId/event"

Write-Host ""
Write-Host "Restart Gateway..."
openclaw gateway restart 2>&1 | Out-Host
Write-Host "Done. Test in Feishu DM."
