# 打开飞书开发者后台与 Dify 控制台（App ID 从 .env 读取）
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$appId = ""
Get-Content (Join-Path $Root ".env") -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^FEISHU_APP_ID=(.+)$') { $appId = $Matches[1].Trim() }
}
if ($appId) {
    Start-Process "https://open.feishu.cn/app/$appId/event"
} else {
    Start-Process "https://open.feishu.cn/app"
}
Start-Process "http://localhost/apps"
Write-Host "Feishu: Event Subscription -> HTTP server URL (see feishu_dify.local.url)"
Write-Host "  Add event: im.message.receive_v1"
Write-Host "Dify: http://localhost/apps -> Feishu Bot -> add LLM model and publish workflow"
