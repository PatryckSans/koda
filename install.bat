@echo off
title KODA Installer
color 0B
echo.
echo   ██▄▀  █▀█  █▀▄  ▄▀█
echo   █░█  █▄█  █▄▀  █▀█
echo   Kiro Operator Dashboard Application
echo.
echo ================================================
echo   Installing KODA...
echo ================================================
echo.

:: Check Python
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    where python3 >nul 2>&1 && set PYTHON=python3
)

if not defined PYTHON (
    color 0E
    echo [!] Python not found.
    echo.
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        set /p INST="Install Python automatically via winget? [Y/n]: "
        if /i not "%INST%"=="n" (
            echo Installing Python 3.12...
            winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            if %errorlevel% neq 0 (
                color 0C
                echo [ERROR] Python installation failed.
                pause
                exit /b 1
            )
            :: Refresh PATH
            set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
            set PYTHON=python
            echo [OK] Python installed
        ) else (
            color 0C
            echo [ERROR] Python 3.8+ is required.
            pause
            exit /b 1
        )
    ) else (
        color 0C
        echo [ERROR] Python 3.8+ is required and winget is not available.
        echo Download from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
)

:: Verify Python version
%PYTHON% -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python 3.8+ is required. You have an older version.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('%PYTHON% --version') do echo [OK] %%i

:: Check WSL
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] WSL is NOT installed. kiro-cli requires WSL to run on Windows.
    echo [!] Install WSL: wsl --install
    pause
    exit /b 1
)
echo [OK] WSL available

:: Check kiro-cli inside WSL
wsl kiro-cli --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo [!] kiro-cli is NOT installed inside WSL. KODA requires it to function.
    echo [!] Open WSL and install from: https://kiro.dev/docs/cli/install/
    echo.
    set /p CONT="Continue anyway? [y/N]: "
    if /i not "%CONT%"=="y" exit /b 1
    color 0B
) else (
    echo [OK] kiro-cli installed in WSL
)

:: Set paths
set INSTALL_DIR=%USERPROFILE%\.koda
set VENV_DIR=%INSTALL_DIR%\venv

:: Remove previous
if exist "%INSTALL_DIR%" (
    echo Removing previous installation...
    rmdir /s /q "%INSTALL_DIR%"
)

:: Download
echo Downloading KODA...
set TMP_DIR=%TEMP%\koda_install
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

powershell -Command "Invoke-WebRequest -Uri 'https://github.com/PatryckSans/koda/archive/refs/heads/main.zip' -OutFile '%TMP_DIR%\koda.zip' -UseBasicParsing"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)

powershell -Command "Expand-Archive -Path '%TMP_DIR%\koda.zip' -DestinationPath '%TMP_DIR%' -Force"
mkdir "%INSTALL_DIR%"
xcopy "%TMP_DIR%\koda-main\kiro_tui" "%INSTALL_DIR%\kiro_tui\" /s /e /q >nul
copy "%TMP_DIR%\koda-main\pyproject.toml" "%INSTALL_DIR%\" >nul
rmdir /s /q "%TMP_DIR%"
echo [OK] Downloaded

:: Create venv
echo Creating virtual environment...
%PYTHON% -m venv "%VENV_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
pip install --quiet --upgrade pip
pip install --quiet -e "%INSTALL_DIR%"
echo [OK] Dependencies installed

:: Create launcher
(
echo @echo off
echo call "%VENV_DIR%\Scripts\activate.bat"
echo python -m kiro_tui.main %%*
) > "%INSTALL_DIR%\koda.bat"
echo [OK] Launcher created

:: Add to PATH
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path','User') + ';%INSTALL_DIR%', 'User')"
echo [OK] Added to PATH

:: Download icon
echo Downloading icon...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/PatryckSans/koda/main/koda-logo.png' -OutFile '%INSTALL_DIR%\koda-logo.png' -UseBasicParsing"

:: Convert PNG to ICO for shortcut
powershell -Command "Add-Type -AssemblyName System.Drawing; $img=[System.Drawing.Image]::FromFile('%INSTALL_DIR%\koda-logo.png'); $icon=[System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]$img).GetHicon()); $fs=[System.IO.File]::Create('%INSTALL_DIR%\koda.ico'); $icon.Save($fs); $fs.Close()" 2>nul
echo [OK] Icon ready

:: Desktop shortcut
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\KODA.lnk'); $s.TargetPath='cmd.exe'; $s.Arguments='/k \"%INSTALL_DIR%\koda.bat\"'; $s.WorkingDirectory='%USERPROFILE%'; $s.Description='KODA - Kiro Operator Dashboard Application'; $s.IconLocation='%INSTALL_DIR%\koda.ico,0'; $s.Save()"
echo [OK] Desktop shortcut created

:: Done
echo.
color 0A
echo ================================================
echo   KODA installed successfully!
echo ================================================
echo.
echo   Run: koda
echo   (Restart terminal if command not found)
echo.
pause
