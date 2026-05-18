# 本地开发：从 Gitee 拉取完整 main 分支（与服务器正式环境同源）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

git fetch origin
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git checkout main
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git pull origin main
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: 已与 origin/main 同步" -ForegroundColor Green
git log -1 --oneline
