# KODA - Kiro Operator Dashboard Application
# Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/patrycksans/koda/main/install.ps1 | iex

function Install-Koda {
    $ErrorActionPreference = "Stop"
    $REPO_URL = "https://github.com/patrycksans/koda/archive/refs/heads/main.zip"
    $INSTALL_DIR = "$env:USERPROFILE\.koda"
    $VENV_DIR = "$INSTALL_DIR\venv"

    function Write-Info($msg)  { Write-Host "[KODA] $msg" -ForegroundColor Cyan }
    function Write-Ok($msg)    { Write-Host "[OK] $msg" -ForegroundColor Green }
    function Write-Warn($msg)  { Write-Host "[!] $msg" -ForegroundColor Yellow }

    Write-Host ""
    Write-Host "  ██▄▀  █▀█  █▀▄  ▄▀█" -ForegroundColor Cyan
    Write-Host "  █░█  █▄█  █▄▀  █▀█" -ForegroundColor Cyan
    Write-Host "  Kiro Operator Dashboard Application" -ForegroundColor Cyan
    Write-Host ""

    # --- Find or install Python 3.8+ ---
    function Find-Python {
        try {
            $out = & py -3 --version 2>$null
            if ($LASTEXITCODE -eq 0 -and $out -match 'Python (\d+)\.(\d+)') {
                if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) { return "py -3" }
            }
        } catch {}
        foreach ($pattern in @(
            "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
            "$env:PROGRAMFILES\Python3*\python.exe"
        )) {
            $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
            if ($found) {
                try {
                    $out = & $found.FullName --version 2>$null
                    if ($out -match 'Python (\d+)\.(\d+)' -and [int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) {
                        return "`"$($found.FullName)`""
                    }
                } catch {}
            }
        }
        try {
            $out = & python --version 2>$null
            if ($LASTEXITCODE -eq 0 -and $out -match 'Python (\d+)\.(\d+)') {
                if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) { return "python" }
            }
        } catch {}
        return $null
    }

    $python = Find-Python
    if (-not $python) {
        Write-Info "Python not found. Installing Python 3.12..."
        $pyInstaller = Join-Path $env:TEMP "python-installer.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
        Write-Info "Running Python installer (this may take a minute)..."
        Start-Process -FilePath $pyInstaller -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1" -Wait
        Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        $python = Find-Python
        if (-not $python) {
            Write-Host "[ERROR] Python install failed. Install manually from https://www.python.org/downloads/" -ForegroundColor Red
            return
        }
        Write-Ok "Python installed"
    }
    Write-Ok "Python: $(Invoke-Expression "$python --version")"

    # --- Check WSL ---
    try {
        $wslStatus = wsl --status 2>&1
        if ($LASTEXITCODE -ne 0) { throw "no wsl" }
        Write-Ok "WSL available"
    } catch {
        Write-Host "[ERROR] WSL is NOT installed. kiro-cli requires WSL." -ForegroundColor Red
        Write-Host "Install with: wsl --install" -ForegroundColor Yellow
        return
    }

    # --- Check kiro-cli inside WSL ---
    $KIRO_VERSION = "1.28.1"
    $needInstall = $true
    try {
        $kiroVer = wsl kiro-cli --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $kiroVer -match '(\d+\.\d+\.\d+)') {
            if ($Matches[1] -eq $KIRO_VERSION) {
                Write-Ok "kiro-cli $KIRO_VERSION"
                $needInstall = $false
            } else {
                Write-Warn "kiro-cli $($Matches[1]) found, need $KIRO_VERSION"
            }
        }
    } catch {}

    if ($needInstall) {
        Write-Info "Installing kiro-cli $KIRO_VERSION inside WSL..."
        $installOut = wsl bash -c "curl -fsSL https://cli.kiro.dev/install 2>/dev/null | bash 2>&1"
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Install script output:"
            $installOut | ForEach-Object { Write-Host "  $_" }
        }
        try {
            $kiroVer = wsl kiro-cli --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "kiro-cli installed: $kiroVer"
            } else { throw "fail" }
        } catch {
            Write-Warn "kiro-cli install failed. Install manually: https://kiro.dev/docs/cli/install/"
            $reply = Read-Host "Continue anyway? [y/N]"
            if ($reply -ne "y" -and $reply -ne "Y") { return }
        }
    }

    # --- Remove previous ---
    if (Test-Path $INSTALL_DIR) {
        Write-Info "Removing previous installation..."
        Remove-Item -Recurse -Force $INSTALL_DIR
    }

    # --- Download and extract ---
    Write-Info "Downloading KODA..."
    New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
    $tmp = Join-Path $env:TEMP "koda_install"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null

    $zipPath = Join-Path $tmp "koda.zip"
    Invoke-WebRequest -Uri $REPO_URL -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $tmp -Force

    Copy-Item -Recurse "$tmp\koda-main\kiro_tui" "$INSTALL_DIR\"
    Copy-Item "$tmp\koda-main\pyproject.toml" "$INSTALL_DIR\"
    Remove-Item -Recurse -Force $tmp
    Write-Ok "Downloaded to $INSTALL_DIR"

    # --- Create venv and install ---
    Write-Info "Creating virtual environment..."
    Invoke-Expression "$python -m venv $VENV_DIR"
    & "$VENV_DIR\Scripts\pip.exe" install --quiet --upgrade pip
    & "$VENV_DIR\Scripts\pip.exe" install --quiet -e $INSTALL_DIR
    Write-Ok "Dependencies installed"

    # --- Create launcher bat ---
    $launcher = "$INSTALL_DIR\koda.bat"
    @"
@echo off
call "$VENV_DIR\Scripts\activate.bat"
python -m kiro_tui.main %*
"@ | Set-Content -Path $launcher
    Write-Ok "Launcher created"

    # --- Add to PATH ---
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$INSTALL_DIR*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$INSTALL_DIR", "User")
        Write-Ok "Added to PATH (restart terminal to use 'koda' command)"
    }

    # --- Download icon ---
    $iconPng = "$INSTALL_DIR\koda-logo.png"
    $iconIco = "$INSTALL_DIR\koda.ico"
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/PatryckSans/koda/main/koda-logo.png" -OutFile $iconPng -UseBasicParsing
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/PatryckSans/koda/main/koda-logo.ico" -OutFile $iconIco -UseBasicParsing
        Write-Ok "Icon ready"
    } catch { Write-Warn "Could not download icon" }

    # --- Ensure Windows Terminal is installed ---
    $wt = Get-Command wt.exe -ErrorAction SilentlyContinue
    if (-not $wt) {
        Write-Info "Installing Windows Terminal..."
        try {
            winget install --id Microsoft.WindowsTerminal --accept-source-agreements --accept-package-agreements --silent 2>$null
            $wt = Get-Command wt.exe -ErrorAction SilentlyContinue
            if ($wt) { Write-Ok "Windows Terminal installed" }
            else { Write-Warn "Windows Terminal install failed, using cmd.exe" }
        } catch { Write-Warn "Could not install Windows Terminal, using cmd.exe" }
    }

    # --- Desktop shortcut ---
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$desktop\KODA.lnk")
    if ($wt) {
        $shortcut.TargetPath = $wt.Source
        $shortcut.Arguments = "--title KODA cmd /c `"$launcher`""
        Write-Ok "Using Windows Terminal"
    } else {
        $shortcut.TargetPath = "cmd.exe"
        $shortcut.Arguments = "/c `"$launcher`""
    }
    $shortcut.WorkingDirectory = $env:USERPROFILE
    $shortcut.Description = "KODA - Kiro Operator Dashboard Application"
    if (Test-Path $iconIco) { $shortcut.IconLocation = "$iconIco,0" }
    $shortcut.Save()
    Write-Ok "Desktop shortcut created"

    # --- Start Menu shortcut ---
    $startMenu = [Environment]::GetFolderPath("StartMenu")
    $startDir = "$startMenu\Programs"
    if (Test-Path $startDir) {
        Copy-Item "$desktop\KODA.lnk" "$startDir\KODA.lnk" -Force
        Write-Ok "Start Menu shortcut created"
    }

    # --- Done ---
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "  KODA installed successfully!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Run:  koda"
    Write-Host "  (Restart terminal if 'koda' is not found)"
    Write-Host ""
}

try { Install-Koda } catch { Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red }
Read-Host "Press Enter to close"
