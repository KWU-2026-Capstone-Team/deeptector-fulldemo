# One-time setup on a new PC. Run from this repository's root (the Service folder):
#   .\Setup-Workspace.ps1
# Needs: Git, Windows Python 3.11 (py -3.11), Node.js 20+.
# Safe to re-run: every step skips work that is already done.
#
# Resulting layout (same as the original development PC):
#   <workspace>\Service\                                   <- this repo
#   <workspace>\Service\AI-Generated-Media-Detection\      <- team model repo (weights included)
#   <workspace>\deepGame\                                  <- team game repo (clips + answer catalog)
param(
    [string]$ModelRepo = 'https://github.com/KWU-2026-Capstone-Team/AI-Generated-Media-Detection.git',
    [string]$GameRepo = 'https://github.com/KWU-2026-Capstone-Team/deepGame.git',
    [string]$GameCommit = '85d18621a8d82e7299036aa8725b150932b1a617'
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'deeptector-backend'
$modelRoot = Join-Path $root 'AI-Generated-Media-Detection'
$modelDir = Join-Path $modelRoot 'deepfake_detector'
$gameRoot = Join-Path (Split-Path $root -Parent) 'deepGame'

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Check($ok, $message) { if (!$ok) { throw $message } }

Step 'Checking tools'
Check (Get-Command git -ErrorAction SilentlyContinue) 'Git is required: https://git-scm.com/download/win'
Check (Get-Command node -ErrorAction SilentlyContinue) 'Node.js 20+ is required: https://nodejs.org/'
& py -3.11 -c "import sys" 2>$null
Check ($LASTEXITCODE -eq 0) 'Windows Python 3.11 is required: winget install --id Python.Python.3.11 -e'

Step 'Model repository (weights are tracked in git, ~420 MB)'
if (!(Test-Path -LiteralPath (Join-Path $modelDir 'infer.py'))) {
    git clone --branch main --single-branch $ModelRepo $modelRoot
    Check ($LASTEXITCODE -eq 0) 'Model repository clone failed.'
} else { Write-Host 'already present' }

Step 'Game repository (clips + answers stay local; never copied into this repo)'
if (!(Test-Path -LiteralPath (Join-Path $gameRoot 'src\data\videos.json'))) {
    git clone $GameRepo $gameRoot
    Check ($LASTEXITCODE -eq 0) 'Game repository clone failed.'
    git -C $gameRoot checkout --quiet $GameCommit
} else { Write-Host 'already present' }

Step 'API environment (.venv)'
$api = Join-Path $backend '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $api)) { & py -3.11 -m venv (Join-Path $backend '.venv') }
& $api -m pip install --disable-pip-version-check -q -r (Join-Path $backend 'requirements-lock.txt')
Check ($LASTEXITCODE -eq 0) 'API dependency installation failed.'

Step 'Model environment (.venv-model, CPU PyTorch)'
$model = Join-Path $backend '.venv-model\Scripts\python.exe'
if (!(Test-Path -LiteralPath $model)) { & py -3.11 -m venv (Join-Path $backend '.venv-model') }
& $model -m pip install --disable-pip-version-check -q -r (Join-Path $backend 'requirements-model-lock.txt')
Check ($LASTEXITCODE -eq 0) 'Model dependency installation failed.'

Step 'Frontend build'
Push-Location (Join-Path $root 'frontend')
try {
    if (!(Test-Path 'node_modules')) { & npm.cmd ci --no-audit --no-fund; Check ($LASTEXITCODE -eq 0) 'npm ci failed.' }
    & npm.cmd run build
    Check ($LASTEXITCODE -eq 0) 'Frontend build failed.'
} finally { Pop-Location }

Step 'Register game clips and saved AI scores'
Push-Location $backend
try {
    $data = Join-Path $backend 'data\integrated'
    & $api -m app.import_deepgame $gameRoot --data-dir $data
    Check ($LASTEXITCODE -eq 0) 'Game import failed.'
    # Saved model scores let the human-vs-AI game work without re-running the model (~25 min).
    & $api -m app.evaluate_games --data-dir $data --import-json (Join-Path $backend 'seeds\game_clip_evaluations.json') --model-dir $modelDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Saved scores do not match this model; evaluating the clips now (about 25 minutes)...' -ForegroundColor Yellow
        & $model -m app.evaluate_games --data-dir $data --model-dir $modelDir
        Check ($LASTEXITCODE -eq 0) 'Game evaluation failed.'
    }
} finally { Pop-Location }

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host '  Local service (game + analysis):  .\Start-Service.ps1 -Mode real    ->  http://127.0.0.1:5173/'
Write-Host '  Public analysis-only link:        .\Start-PublicTunnel.ps1          (needs: winget install --id Cloudflare.cloudflared -e)'
