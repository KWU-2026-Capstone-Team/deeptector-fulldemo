# Publish the service from this PC through a Cloudflare Quick Tunnel.
#   .\Start-PublicTunnel.ps1             # analysis only (prints https://*.trycloudflare.com)
#   .\Start-PublicTunnel.ps1 -WithGames  # analysis + human-vs-AI game
#   .\Start-PublicTunnel.ps1 -Build      # rebuild the public frontend first (after UI changes)
# Sessions are rate-limited per client IP, and the server binds to 127.0.0.1 so it is reachable
# only through the tunnel. Ctrl+C stops both the tunnel and the server.
# -WithGames serves the local deepGame clips (FaceForensics++-derived; public redistribution
# rights unverified), so share that link only for short demos.
param(
    [switch]$Build,
    [switch]$WithGames,
    [int]$Port = 7860,
    [string]$ModelDir = (Join-Path $PSScriptRoot 'AI-Generated-Media-Detection\deepfake_detector')
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'deeptector-backend'
$apiPython = Join-Path $backend '.venv\Scripts\python.exe'
$modelPython = Join-Path $backend '.venv-model\Scripts\python.exe'
$publicRoot = Join-Path $root '.public'
$publicFrontend = Join-Path $publicRoot $(if ($WithGames) { 'frontend-games' } else { 'frontend' })
$publicData = Join-Path $publicRoot 'data'
$gamesFlag = $(if ($WithGames) { '1' } else { '0' })

$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (!$cloudflared) { $cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe' }
if (!(Test-Path -LiteralPath $cloudflared)) { throw 'cloudflared not found: winget install --id Cloudflare.cloudflared -e' }
foreach ($p in $apiPython, $modelPython) { if (!(Test-Path -LiteralPath $p)) { throw "Missing $p (see deeptector-backend/README.md)" } }
if (!(Test-Path -LiteralPath (Join-Path $ModelDir 'infer.py'))) { throw "Model folder not found: $ModelDir" }

if ($Build -or !(Test-Path (Join-Path $publicFrontend 'index.html'))) {
    Push-Location (Join-Path $root 'frontend')
    try {
        $env:NEXT_PUBLIC_ENABLE_GAMES = $gamesFlag; $env:NEXT_PUBLIC_DEPLOYMENT = 'public'
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Public frontend build failed.' }
        if (Test-Path $publicFrontend) { Remove-Item $publicFrontend -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $publicRoot | Out-Null
        Copy-Item 'out' $publicFrontend -Recurse
    } finally {
        Remove-Item Env:NEXT_PUBLIC_ENABLE_GAMES, Env:NEXT_PUBLIC_DEPLOYMENT -ErrorAction SilentlyContinue
        # Restore the regular (games-on) build used by Start-Service.ps1.
        & npm.cmd run build | Out-Null
        Pop-Location
    }
}

if ($WithGames) {
    # Register the game clips and saved AI scores in the public data folder (idempotent).
    $gameRoot = Join-Path (Split-Path $root -Parent) 'deepGame'
    if (!(Test-Path -LiteralPath (Join-Path $gameRoot 'src\data\videos.json'))) { throw "deepGame checkout not found: $gameRoot (run Setup-Workspace.ps1)" }
    Push-Location $backend
    try {
        & $apiPython -m app.import_deepgame $gameRoot --data-dir $publicData
        if ($LASTEXITCODE -ne 0) { throw 'Game import failed.' }
        & $apiPython -m app.evaluate_games --data-dir $publicData --import-json (Join-Path $backend 'seeds\game_clip_evaluations.json') --model-dir $ModelDir
        if ($LASTEXITCODE -ne 0) { Write-Host 'Saved AI scores do not match this model; the game runs without AI comparison.' -ForegroundColor Yellow }
    } finally { Pop-Location }
}

$env:DEEPTECTOR_ENABLE_GAMES = $gamesFlag
$env:DEEPTECTOR_SESSION_RATE_PER_IP_HOUR = '30'
$env:DEEPTECTOR_CLIENT_IP_HEADER = 'cf-connecting-ip'
$env:DEEPTECTOR_SESSION_TTL_HOURS = '24'
$env:DEEPTECTOR_MAX_QUEUED_PER_SESSION = '2'
$env:DEEPTECTOR_MAX_ACTIVE_GLOBAL = '20'
$env:DEEPTECTOR_JOB_TIMEOUT_SECONDS = '900'

$serverArgs = @(
    (Join-Path $backend 'scripts\run_integrated.py'), '--port', "$Port", '--mode', 'real', '--host', '127.0.0.1',
    '--data-dir', $publicData, '--frontend-dir', $publicFrontend,
    '--model-dir', $ModelDir, '--worker-python', $modelPython
)
$server = Start-Process -FilePath $apiPython -ArgumentList ($serverArgs | ForEach-Object { '"' + $_ + '"' }) -WorkingDirectory $backend -NoNewWindow -PassThru
try {
    $ready = $false
    for ($i = 0; $i -lt 60 -and !$server.HasExited; $i++) {
        try { if ((Invoke-RestMethod "http://127.0.0.1:$Port/health/worker" -TimeoutSec 2).ready) { $ready = $true; break } } catch {}
        Start-Sleep -Seconds 1
    }
    if (!$ready) { throw 'Public server did not become ready.' }
    Write-Host "Public server ready on 127.0.0.1:$Port. Opening tunnel..." -ForegroundColor Green
    $urlFile = Join-Path $publicRoot 'current-url.txt'
    Remove-Item -LiteralPath $urlFile -ErrorAction SilentlyContinue
    # cloudflared logs to stderr; scan it for the quick-tunnel address and save it for later lookup.
    $ErrorActionPreference = 'Continue'
    & $cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$Port" 2>&1 | ForEach-Object {
        $line = "$_"
        Write-Host $line
        if ($line -match 'https://[a-z0-9-]+\.trycloudflare\.com' -and !(Test-Path -LiteralPath $urlFile)) {
            Set-Content -LiteralPath $urlFile -Value $Matches[0] -Encoding utf8
            Write-Host ''
            Write-Host "  PUBLIC URL: $($Matches[0])   (saved to .public\current-url.txt)" -ForegroundColor Cyan
            Write-Host '  Close this window or press Ctrl+C to stop the public site.' -ForegroundColor Cyan
            Write-Host ''
        }
    }
} finally {
    if (!$server.HasExited) { taskkill /PID $server.Id /T /F | Out-Null }
    Remove-Item -LiteralPath (Join-Path $publicRoot 'current-url.txt') -ErrorAction SilentlyContinue
    Write-Host 'Public server stopped.'
}
