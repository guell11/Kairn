param([switch]$SetupOnly)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
try {
    . (Join-Path $PSScriptRoot "scripts\bootstrap_windows.ps1")
    $studioPython = Initialize-StudioEnvironment -ProjectRoot $PSScriptRoot
    if ($SetupOnly) {
        & $studioPython (Join-Path $PSScriptRoot "scripts\doctor.py")
        exit $LASTEXITCODE
    }
    Write-Host "Iniciando Kaggle Studio..."
    $startupLog = Join-Path $PSScriptRoot ".kaggle-studio\startup-error.log"
    # Continue lets native stderr reach the log in Windows PowerShell 5.1.
    $ErrorActionPreference = "Continue"
    & $studioPython (Join-Path $PSScriptRoot "main.py") 2> $startupLog
    $appExitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($appExitCode -ne 0) {
        Write-Host "Falha ao abrir. Log: $startupLog"
        Get-Content -LiteralPath $startupLog
        exit $appExitCode
    }
    exit 0
} catch {
    Write-Host "Falha ao preparar Kaggle Studio: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
