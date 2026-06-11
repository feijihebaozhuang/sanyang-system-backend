# Run from repo root: .\scripts\ops\verify_feishu_dify_integration.ps1
$ErrorActionPreference = "Continue"
$Out = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "verify_feishu_dify.out.txt"
$lines = @()
function Add($s) { $script:lines += $s; Write-Host $s }

Add "=== 1 docker-api-1 health ==="
Add (wsl docker inspect docker-api-1 --format "{{.State.Health.Status}}" 2>&1 | Out-String).Trim()

Add "=== 2 bridge http://127.0.0.1:5099/ ==="
try {
    $r = Invoke-RestMethod http://127.0.0.1:5099/ -TimeoutSec 5
    Add ($r | ConvertTo-Json -Compress)
} catch { Add "FAIL: $_" }

Add "=== 3 Dify chat-messages ==="
$chat = wsl curl -s -w "`nHTTP:%{http_code}" -X POST http://127.0.0.1/v1/chat-messages `
  -H "Authorization: Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx" `
  -H "Content-Type: application/json" `
  -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"verify-test"}' 2>&1
Add ($chat | Out-String).Trim()

Add "=== 4 ngrok tunnels ==="
try {
    $t = Invoke-RestMethod http://127.0.0.1:4040/api/tunnels -TimeoutSec 5
    Add ($t | ConvertTo-Json -Depth 6 -Compress)
} catch { Add "FAIL: $_" }

Add "=== 5 feishu_dify.err (last 20) ==="
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$err = Join-Path $root "feishu_dify.err"
$log = Join-Path $root "feishu_dify.log"
if (Test-Path $err) { Get-Content $err -Tail 20 | ForEach-Object { Add $_ } } else { Add "(missing)" }
Add "=== 5 feishu_dify.log (last 20) ==="
if (Test-Path $log) { Get-Content $log -Tail 20 | ForEach-Object { Add $_ } } else { Add "(missing)" }

$lines | Set-Content $Out -Encoding utf8
Write-Host "Wrote $Out"
