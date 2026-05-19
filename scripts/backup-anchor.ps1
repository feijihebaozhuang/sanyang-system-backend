# 本地 Windows：为当前仓库打备份包（配合 Git 标签 v8.33）
# 用法: .\scripts\backup-anchor.ps1 [-Version 8.33]
param(
    [string]$Version = "8.33"
)

$ErrorActionPreference = "Stop"
$Tag = "v$Version"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Set-Location $Root
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutDir = Join-Path $Root "backups\anchor_${Tag}_${Stamp}"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

git fetch origin --tags 2>$null
$ref = $Tag
try { git rev-parse $Tag 2>$null | Out-Null } catch { $ref = "HEAD" }

$zip = Join-Path $OutDir "code_${Tag}.zip"
git archive --format=zip -o $zip $ref
Write-Host "[OK] $zip"

@"
锚点版本: $Tag
备份时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Git: $(git rev-parse $ref)
客服: app_cs.py :3001
生产: app_production.py :3002
"@ | Set-Content (Join-Path $OutDir "ANCHOR.txt") -Encoding UTF8

Write-Host "完成: $OutDir"
Write-Host "远程标签: git push origin $Tag"
