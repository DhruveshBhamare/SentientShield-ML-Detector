param(
  [string]$PythonExe = "",
  [string]$Host = "127.0.0.1",
  [int]$Port = 10000
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
  } else {
    $PythonExe = "python"
  }
}

$env:PYTHONUNBUFFERED = "1"

& $PythonExe -m uvicorn src.main:app --host $Host --port $Port

