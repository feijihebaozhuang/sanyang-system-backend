# 三套独立：OpenClaw / Dify / Cursor — 各用各的飞书应用 + DeepSeek，互不混用
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Desktop = [Environment]::GetFolderPath("Desktop")

# --- 凭证（三套）---
$OpenClawFeishu = @{
    AppId     = "cli_a97ca4949b785cb5"
    AppSecret = "HXiSsEIbJLtYRGoUS0RahfvN0K3J7rNo"
    DeepSeek  = "sk-dcf59140596a492da2b6c78ea38604a6"
}
$DifyFeishu = @{
    AppId     = "cli_a96c15d3dcf8dbcd"
    AppSecret = "iyUTIAtme5j4QI3YL6jFQghMUvinBXNI"
    DeepSeek  = "sk-abaf056a56e745b396f0b7937ea503bb"
}
$CursorFeishu = @{
    AppId     = "cli_a96c20180038dbde"
    AppSecret = "8jSaUPBDhnMabpZAp67avwD4LVX1KuaC"
}

Write-Host "=== 1/3 OpenClaw ==="
$auth = Join-Path $env:USERPROFILE ".openclaw\agents\main\agent\auth-profiles.json"
@{ deepseek = @{ baseUrl = "https://api.deepseek.com/v1"; apiKey = $OpenClawFeishu.DeepSeek } } |
    ConvertTo-Json | Set-Content $auth -Encoding UTF8

$oc = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"
$cfg = Get-Content $oc -Raw | ConvertFrom-Json
$cfg.channels.feishu.enabled = $true
$cfg.channels.feishu.appId = $OpenClawFeishu.AppId
$cfg.channels.feishu.appSecret = $OpenClawFeishu.AppSecret
$cfg.channels.feishu.connectionMode = "websocket"
$cfg.channels.feishu.dmPolicy = "open"
$cfg.agents.defaults.model.primary = "deepseek/deepseek-v4-flash"
$cfg.agents.defaults.thinkingDefault = "off"
$cfg | ConvertTo-Json -Depth 12 | Set-Content $oc -Encoding UTF8
Write-Host "  飞书 $($OpenClawFeishu.AppId) + DeepSeek $($OpenClawFeishu.DeepSeek.Substring(0,8))..."

Write-Host "=== 2/3 Dify (.env 仅 Dify 机器人) ==="
$envPath = Join-Path $Root ".env"
$lines = @(
    "# --- OpenClaw 勿用此段飞书；Dify 专用 HTTP 机器人 ---",
    "FEISHU_DIFY_ENABLED=true",
    "FEISHU_APP_ID=$($DifyFeishu.AppId)",
    "FEISHU_APP_SECRET=$($DifyFeishu.AppSecret)",
    "FEISHU_VERIFICATION_TOKEN=",
    "FEISHU_ENCRYPT_KEY=",
    "FEISHU_GROUP_REPLY_ALL=false",
    "DIFY_API_BASE=http://127.0.0.1/v1",
    "DIFY_API_KEY=app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx",
    "DIFY_TIMEOUT=120",
    "DIFY_DEEPSEEK_API_KEY=$($DifyFeishu.DeepSeek)",
    "FEISHU_USE_OLLAMA_FALLBACK=true",
    "OLLAMA_BASE=http://127.0.0.1:11434",
    "OLLAMA_MODEL=qwen2.5:0.5b"
)
if (Test-Path $envPath) {
    $old = Get-Content $envPath -Raw
    $keys = @("FEISHU_DIFY_ENABLED", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "DIFY_", "OLLAMA_", "FEISHU_USE_OLLAMA", "FEISHU_VERIFICATION", "FEISHU_ENCRYPT", "FEISHU_GROUP")
    $kept = Get-Content $envPath | Where-Object {
        $line = $_
        -not ($keys | Where-Object { $line -match "^\s*$([regex]::Escape($_))\s*=" })
    }
    ($kept + "" + $lines) | Set-Content $envPath -Encoding UTF8
} else {
    $lines | Set-Content $envPath -Encoding UTF8
}
Write-Host "  飞书 $($DifyFeishu.AppId) + DeepSeek $($DifyFeishu.DeepSeek.Substring(0,8))... (Dify 控制台也需填)"

Write-Host "=== 3/3 Cursor 飞书桥接 ==="
$cfgDir = Join-Path $env:USERPROFILE ".config\feishu-agent-bridge"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
@{
    appId     = $CursorFeishu.AppId
    appSecret = $CursorFeishu.AppSecret
    timeout   = 300000
    directory = ($Root -replace '\\', '/')
    logLevel  = "info"
} | ConvertTo-Json | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $cfgDir "feishu.json"), $_, [System.Text.UTF8Encoding]::new($false))
}
Write-Host "  Feishu $($CursorFeishu.AppId) -> cursor agent (no DeepSeek key)"

Write-Host ""
Write-Host "See docs\THREE_BOTS.md"
Write-Host "Run: .\scripts\start_all_three.ps1"
