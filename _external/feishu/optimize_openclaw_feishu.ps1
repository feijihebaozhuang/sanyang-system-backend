# OpenClaw 飞书回复慢 — 一键优化（本机执行，需已安装 openclaw）
# 根因多为：事件循环被占满、thinking=medium、Dify Docker 抢 CPU、插件过多

$ErrorActionPreference = "Stop"

Write-Host "==> 关闭 thinking、换 v4-flash、缩小 bootstrap、限制插件..."
openclaw config set agents.defaults.thinkingDefault off 2>&1 | Out-Host
openclaw config set agents.defaults.model.primary deepseek/deepseek-v4-flash 2>&1 | Out-Host
openclaw config set agents.defaults.bootstrapMaxChars 4000 2>&1 | Out-Host
openclaw config set agents.defaults.bootstrapTotalMaxChars 20000 2>&1 | Out-Host

$cfgPath = "$env:USERPROFILE\.openclaw\openclaw.json"
$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
if (-not $cfg.plugins) { $cfg | Add-Member -NotePropertyName plugins -NotePropertyValue (@{}) }
$cfg.plugins | Add-Member -NotePropertyName allow -NotePropertyValue @("feishu","deepseek","memory-core") -Force
$cfg | ConvertTo-Json -Depth 12 | Set-Content $cfgPath -Encoding UTF8

$gw = "$env:USERPROFILE\.openclaw\gateway.cmd"
if (Test-Path $gw) {
    $t = Get-Content $gw -Raw
    if ($t -notmatch "OPENCLAW_SKIP_CANVAS_HOST") {
        $t = $t -replace '(set "OPENCLAW_SERVICE_VERSION=[^"]+")', "`$1`r`nset `"OPENCLAW_SKIP_CANVAS_HOST=1`""
        Set-Content $gw $t -Encoding ASCII
        Write-Host "==> 已写入 OPENCLAW_SKIP_CANVAS_HOST=1 到 gateway.cmd"
    }
}

Write-Host "==> 可选：停止 WSL 内 Dify（释放 CPU）..."
wsl -e bash -c "cd /opt/services/dify/docker 2>/dev/null && docker compose down" 2>&1 | Out-Host

Write-Host "==> 重启 OpenClaw Gateway..."
openclaw gateway restart 2>&1 | Out-Host
Write-Host "完成。请在飞书给机器人发「你好」测速。日志: D:\AppCache\temp\openclaw\openclaw-*.log"
