# 把启动脚本复制到「真实桌面」（本机桌面在 D:\Desktop，不是 C:\Users\...\Desktop）
$ErrorActionPreference = "Stop"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Src = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "desktop_shortcuts"
if (-not (Test-Path $Src)) {
    Write-Host "缺少 $Src 目录"
    exit 1
}
Get-ChildItem $Src -Filter "*.bat" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $Desktop $_.Name) -Force
    Write-Host "已复制 -> $Desktop\$($_.Name)"
}
Write-Host "完成。当前桌面路径: $Desktop"
