# Build onefile EXE (tkinter, no PySide6)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Dist = Join-Path $Root 'dist'
New-Item -ItemType Directory -Force -Path $Dist | Out-Null

$Python = @(
  'C:\Python313\python.exe',
  'C:\Python312\python.exe',
  'C:\Python311\python.exe'
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) { $Python = 'python' }

Write-Host "Using Python: $Python"
& $Python -m pip install -q -r requirements.txt

& $Python -m PyInstaller --noconfirm --clean --windowed --onefile `
  --name FrameInterviewTree `
  --distpath $Dist `
  --workpath (Join-Path $Root 'build') `
  --specpath (Join-Path $Root 'build') `
  --hidden-import defaults `
  --hidden-import prompts `
  --hidden-import tree_store `
  --hidden-import deepseek_client `
  app.py

$src = Join-Path $Dist 'FrameInterviewTree.exe'
if (-not (Test-Path -LiteralPath $src)) {
  throw "Build failed: $src not found"
}

$dstRoot = Join-Path (Split-Path -Parent $Root) 'FrameInterviewTree.exe'
Copy-Item -LiteralPath $src -Destination $dstRoot -Force
Write-Host "Built: $src"
Write-Host "Copied: $dstRoot"
