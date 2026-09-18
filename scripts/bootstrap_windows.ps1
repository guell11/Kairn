# Shared bootstrap for run.bat, setup.bat and run.ps1. No global pip installs.
function Test-StudioPython {
    param([string]$Python, [string]$Probe)
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { return $false }
    try {
        & $Python -c $Probe *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-StudioBasePython {
    foreach ($candidate in @("py", "python")) {
        $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        $arguments = @()
        if ($candidate -eq "py") { $arguments += "-3" }
        $arguments += @("-c", "import sys; assert sys.version_info >= (3, 10); print(sys._base_executable)")
        try {
            $result = & $command.Source @arguments 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $basePython = ([string]($result | Select-Object -Last 1)).Trim()
            if (Test-StudioPython $basePython "import sys, venv; assert sys.version_info >= (3, 10)") {
                return $basePython
            }
        } catch { continue }
    }
    throw "Python 3.10+ nao encontrado. Instale Python 3.12 e tente novamente."
}

function Initialize-StudioEnvironment {
    param([Parameter(Mandatory=$true)][string]$ProjectRoot)
    $projectPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $venvPath = Join-Path $projectPath ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    $statePath = Join-Path $projectPath ".kaggle-studio"
    New-Item -ItemType Directory -Path $statePath -Force | Out-Null

    $valid = (Test-Path -LiteralPath (Join-Path $venvPath "pyvenv.cfg") -PathType Leaf) -and
        (Test-StudioPython $venvPython "import sys, pip, ssl; assert sys.version_info >= (3, 10); assert sys.prefix != sys.base_prefix")
    if (-not $valid) {
        # Resolve a working system interpreter BEFORE touching the broken environment.
        $basePython = Find-StudioBasePython
        if (Test-Path -LiteralPath $venvPath) {
            $resolvedVenv = (Resolve-Path -LiteralPath $venvPath).Path
            $backup = Join-Path $statePath ("venv-backup-" + [guid]::NewGuid().ToString("N"))
            # Both source and destination must remain inside this exact project.
            if ($resolvedVenv -ne [IO.Path]::GetFullPath($venvPath) -or
                [IO.Path]::GetFullPath($backup).StartsWith($projectPath + [IO.Path]::DirectorySeparatorChar) -eq $false -or
                ((Get-Item -LiteralPath $venvPath).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Caminho .venv inesperado. Recuperacao automatica interrompida."
            }
            Write-Host "Ambiente Python incompleto. Recriando .venv; copia anterior preservada em $backup"
            try { Move-Item -LiteralPath $resolvedVenv -Destination $backup -ErrorAction Stop }
            catch { throw "Nao foi possivel preservar .venv. Feche processos usando esse ambiente e tente novamente. $($_.Exception.Message)" }
        } else {
            Write-Host "Criando ambiente Python..."
        }
        & $basePython -m venv $venvPath | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Python falhou ao criar .venv (codigo $LASTEXITCODE)." }
        if (-not (Test-StudioPython $venvPython "import sys, pip, ssl; assert sys.prefix != sys.base_prefix")) {
            throw "Ambiente Python criado, mas validacao falhou."
        }
    }

    $dependencyProbe = "import httpx; from PyQt6.QtWidgets import QApplication; from PyQt6.QtWebEngineWidgets import QWebEngineView"
    if (-not (Test-StudioPython $venvPython $dependencyProbe)) {
        Write-Host "Instalando dependencias..."
        & $venvPython -m pip install -r (Join-Path $projectPath "requirements.txt") | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Instalacao de dependencias falhou (codigo $LASTEXITCODE)." }
        if (-not (Test-StudioPython $venvPython $dependencyProbe)) {
            throw "Dependencias instaladas, mas importacao de PyQt6/WebEngine/httpx falhou."
        }
    }
    return $venvPython
}
