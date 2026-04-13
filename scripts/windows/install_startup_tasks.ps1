param(
  [string]$TaskPrefix = "SentientShield",
  [string]$RepoRoot = ""
)

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
}

$RunApi = Join-Path $RepoRoot "scripts\windows\run_api.ps1"
$RunStreamlit = Join-Path $RepoRoot "scripts\windows\run_streamlit.ps1"

if (-not (Test-Path $RunApi)) {
  throw "Missing file: $RunApi"
}

if (-not (Test-Path $RunStreamlit)) {
  throw "Missing file: $RunStreamlit"
}

$ApiTaskName = "$TaskPrefix API"
$StreamlitTaskName = "$TaskPrefix Streamlit"

$ApiCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$RunApi`""
$StreamlitCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$RunStreamlit`""

schtasks /Create /F /SC ONSTART /RL HIGHEST /TN $ApiTaskName /TR $ApiCmd | Out-Null
schtasks /Create /F /SC ONSTART /RL HIGHEST /TN $StreamlitTaskName /TR $StreamlitCmd | Out-Null

Write-Output "Installed startup tasks: $ApiTaskName, $StreamlitTaskName"
