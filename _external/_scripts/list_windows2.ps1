# 找到所有有控制台窗口的进程
$procs = Get-CimInstance Win32_Process | Where-Object { 
    $_.Name -match 'cmd|python|hermes|node|openclaw|codex' 
} | ForEach-Object {
    $p = $_
    try {
        $hasWindow = (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue).MainWindowHandle -ne 0
    } catch { $hasWindow = $false }
    
    # 也检查控制台窗口
    $consoleTitle = ""
    try {
        $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        if ($proc) { $consoleTitle = $proc.MainWindowTitle }
    } catch {}
    
    [PSCustomObject]@{
        PID = $p.ProcessId
        Name = $p.Name
        Title = if ($consoleTitle) { $consoleTitle } else { "(no window)" }
        CmdLine = $p.CommandLine
    }
}
$procs | Format-Table -AutoSize -Wrap
