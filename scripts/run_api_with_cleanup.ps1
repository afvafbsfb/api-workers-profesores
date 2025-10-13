param(
    [string]$JwtSecret = 'mi_secret_app_local_larga',
    [string]$DelegationSecret = 'mi_secret_delegacion_local_larga',
    [int]$Port = 5000,
    [switch]$NewWindow
)

# Resolve repo root and ensure logs dir
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$LogsDir = Join-Path $RepoRoot 'logs'
New-Item -Path $LogsDir -ItemType Directory -Force | Out-Null

# Remove existing .log files (cleanup before start)
Get-ChildItem -Path $LogsDir -Filter '*.log' -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Set environment variables for this session (mediator and tests expect these)
$env:JWT_SECRET_KEY = $JwtSecret
$env:JWT_DELEGATION_SECRET = $DelegationSecret
# Export additional environment variables so the python process sees them
$env:DEBUG = '1'
$env:FLASK_DEBUG = '1'
$env:APP_ENV = 'development'

# Optional: set FLASK_APP if you run via flask run
$env:FLASK_APP = 'main.py'

$LogFile = Join-Path $LogsDir 'api_stdout.log'

# Build command to run the API (unbuffered output) and tee to log file
# Use single-quotes around paths inside the command string to protect spaces
$Cmd = "cd '$RepoRoot'; if (Test-Path '.venv\Scripts\Activate.ps1') { . '.venv\Scripts\Activate.ps1' } ; python -u main.py 2>&1 | Tee-Object -FilePath '$LogFile'"

if ($NewWindow) {
    # When opening a new window, include explicit env assignments so the new shell inherits them
    $safeCmd = "Set-Location -LiteralPath '$RepoRoot'; `$env:JWT_SECRET_KEY = '$JwtSecret'; `$env:JWT_DELEGATION_SECRET = '$DelegationSecret'; `$env:DEBUG = '1'; `$env:FLASK_DEBUG = '1'; `$env:APP_ENV = 'development'; if (Test-Path '.venv\Scripts\Activate.ps1') { . '.venv\Scripts\Activate.ps1' } ; python -u main.py 2>&1 | Tee-Object -FilePath '$LogFile'"
    Start-Process -FilePath "powershell" -ArgumentList @('-NoExit','-Command',$safeCmd)
} else {
    Invoke-Expression $Cmd
}
