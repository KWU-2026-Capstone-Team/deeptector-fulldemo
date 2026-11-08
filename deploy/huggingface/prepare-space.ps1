# Assemble a Hugging Face Space folder (Docker SDK) from this repository.
# Copies only what the image needs: no venvs, local DBs, uploads, build output, game media or model files.
#   .\deploy\huggingface\prepare-space.ps1 -Target ..\deeptector-space
param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$here = $PSScriptRoot

if (Test-Path -LiteralPath $Target) {
    $existing = Get-ChildItem -LiteralPath $Target -Force | Where-Object { $_.Name -ne '.git' }
    foreach ($item in $existing) { Remove-Item -LiteralPath $item.FullName -Recurse -Force }
} else {
    New-Item -ItemType Directory -Path $Target | Out-Null
}
$dest = (Resolve-Path -LiteralPath $Target).Path

function Copy-Tree($from, $to, [string[]]$excludeDirs) {
    New-Item -ItemType Directory -Force -Path $to | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $from -Force) {
        if ($item.PSIsContainer) {
            if ($excludeDirs -contains $item.Name) { continue }
            Copy-Tree $item.FullName (Join-Path $to $item.Name) $excludeDirs
        } elseif ($item.Extension -notin '.pyc', '.sqlite3', '.log', '.pt', '.pth') {
            Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $to $item.Name)
        }
    }
}

$skip = @('node_modules', 'out', '.next', '.venv', '.venv-model', 'data', '__pycache__', '.pytest_cache', '.ruff_cache', 'tests', 'docs', 'examples', '.git')
Copy-Tree (Join-Path $repo 'frontend') (Join-Path $dest 'frontend') $skip
Copy-Tree (Join-Path $repo 'deeptector-backend') (Join-Path $dest 'deeptector-backend') $skip

Copy-Item (Join-Path $here 'Dockerfile') (Join-Path $dest 'Dockerfile')
Copy-Item (Join-Path $here 'SPACE_README.md') (Join-Path $dest 'README.md')
# Keep LF line endings so bash runs the entrypoint inside the Linux container.
$entry = [IO.File]::ReadAllText((Join-Path $here 'entrypoint.sh')) -replace "`r`n", "`n"
[IO.File]::WriteAllText((Join-Path $dest 'entrypoint.sh'), $entry, (New-Object Text.UTF8Encoding $false))
[IO.File]::WriteAllText((Join-Path $dest '.gitattributes'), "*.sh text eol=lf`n", (New-Object Text.UTF8Encoding $false))

$files = Get-ChildItem -LiteralPath $dest -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.git\\' }
$mb = [Math]::Round((($files | Measure-Object Length -Sum).Sum) / 1MB, 2)
Write-Host "Space folder ready: $dest ($($files.Count) files, $mb MB)"
