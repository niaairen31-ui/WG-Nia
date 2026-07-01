$venv = Test-Path ".\.venv\Scripts\Activate.ps1"
$pp   = $env:PYTHONPATH -eq "src"
if (-not $venv) { Write-Output "WARNING: .venv not found — activate it before verdict commands." }
if (-not $pp)   { Write-Output "WARNING: PYTHONPATH is not 'src' — package resolution will fail." }
exit 0
