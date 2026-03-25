# KODA - Kiro Operator Dashboard Application
# Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/patrycksans/koda/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/patrycksans/koda/archive/refs/heads/main.zip"
$INSTALL_DIR = "$env:USERPROFILE\.koda"
$VENV_DIR = "$INSTALL_DIR\venv"

function Write-Info($msg)  { Write-Host "[KODA] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

Write-Host ""
Write-Host "  ██▄▀  █▀█  █▀▄  ▄▀█" -ForegroundColor Cyan
Write-Host "  █░█  █▄█  █▄▀  █▀█" -ForegroundColor Cyan
Write-Host "  Kiro Operator Dashboard Application" -ForegroundColor Cyan
Write-Host ""

# --- Check Python 3.8+ ---
$python = $null

# Try py launcher first (most reliable on Windows)
try {
    $out = & py -3 --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $out -match 'Python (\d+)\.(\d+)') {
        if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) { $python = "py -3" }
    }
} catch {}

# Try common install paths (avoids Microsoft Store alias)
if (-not $python) {
    $paths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
        "$env:PROGRAMFILES\Python3*\python.exe",
        "$env:PROGRAMFILES(x86)\Python3*\python.exe"
    )
    foreach ($pattern in $paths) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
        if ($found) {
            try {
                $out = & $found.FullName --version 2>$null
                if ($out -match 'Python (\d+)\.(\d+)' -and [int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) {
                    $python = $found.FullName
                }
            } catch {}
            if ($python) { break }
        }
    }
}

# Try plain python (may hit Microsoft Store alias — last resort)
if (-not $python) {
    try {
        $out = & python --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -match 'Python (\d+)\.(\d+)') {
            if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) { $python = "python" }
        }
    } catch {}
}

if (-not $python) { Write-Fail "Python 3.8+ is required. Download from https://www.python.org/downloads/`nTip: If Python is installed, disable Microsoft Store aliases in Settings > Apps > App execution aliases" }
Write-Ok "Python: $(Invoke-Expression """$python"" --version")"

# --- Check WSL ---
try {
    $wslStatus = wsl --status 2>&1
    if ($LASTEXITCODE -ne 0) { throw "no wsl" }
    Write-Ok "WSL available"
} catch {
    Write-Fail "WSL is NOT installed. kiro-cli requires WSL to run on Windows. Install with: wsl --install"
}

# --- Check kiro-cli inside WSL ---
try {
    $kiroVer = wsl kiro-cli --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "no kiro" }
    Write-Ok "kiro-cli installed in WSL"
} catch {
    Write-Warn "kiro-cli is NOT installed inside WSL. KODA requires kiro-cli to function."
    Write-Warn "Open WSL and install from: https://kiro.dev/docs/cli/install/"
    $reply = Read-Host "Continue anyway? [y/N]"
    if ($reply -ne "y" -and $reply -ne "Y") { exit 1 }
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
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/PatryckSans/koda/main/koda-logo.png" -OutFile $iconPng -UseBasicParsing
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/PatryckSans/koda/main/koda-logo.ico" -OutFile $iconIco -UseBasicParsing
Write-Ok "Icon ready"

# --- Desktop shortcut (prefer Windows Terminal) ---
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut("$desktop\KODA.lnk")
$wt = Get-Command wt.exe -ErrorAction SilentlyContinue
if ($wt) {
    $shortcut.TargetPath = $wt.Source
    $shortcut.Arguments = "--title KODA cmd /c `"$launcher`""
    Write-Ok "Using Windows Terminal"
} else {
    $shortcut.TargetPath = "cmd.exe"
    $shortcut.Arguments = "/c `"$launcher`""
    Write-Warn "Windows Terminal not found, using cmd.exe"
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
Read-Host "Press Enter to close"
