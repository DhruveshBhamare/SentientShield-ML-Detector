param(
  [string]$PythonExe = "",
  [string]$ApiUrl = "http://127.0.0.1:10000",
  [int]$Port = 8501,
  [string]$Host = "127.0.0.1"
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

$env:API_URL = $ApiUrl
$env:PUBLIC_BASE_URL = ""

& $PythonExe -m streamlit run src/streamlit_app.py --server.port $Port --server.address $Host

