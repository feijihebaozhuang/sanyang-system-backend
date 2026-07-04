Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object Id, ProcessName, @{N='Title';E={$_.MainWindowTitle}} | Format-Table -AutoSize
Write-Host "---"
Write-Host "Console windows (cmd.exe with windows):"
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cmd.exe' } | Select-Object ProcessId, CommandLine -First 10 | Format-Table -AutoSize
Write-Host "---"
Write-Host "All python/electron/node windows:"
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node|electron|hermes|codex|openclaw' } | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize
