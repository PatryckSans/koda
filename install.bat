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
where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] Python 3.8+ is required.
        echo Download from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during install.
        echo.
        pause
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
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

:: Check kiro-cli
where kiro-cli >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo [!] kiro-cli is NOT installed. KODA requires it to function.
    echo [!] Install from: https://kiro.dev/docs/cli/install/
    echo.
    set /p CONT="Continue anyway? [y/N]: "
    if /i not "%CONT%"=="y" exit /b 1
    color 0B
) else (
    echo [OK] kiro-cli installed
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

:: Desktop shortcut
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\KODA.lnk'); $s.TargetPath='cmd.exe'; $s.Arguments='/k \"%INSTALL_DIR%\koda.bat\"'; $s.WorkingDirectory='%USERPROFILE%'; $s.Description='KODA - Kiro Operator Dashboard Application'; $s.Save()"
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
