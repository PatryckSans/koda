# KODA Uninstaller for Windows
$INSTALL_DIR = "$env:USERPROFILE\.koda"

Write-Host "[KODA] Uninstalling..." -ForegroundColor Cyan

if (Test-Path $INSTALL_DIR) {
    Remove-Item -Recurse -Force $INSTALL_DIR
    Write-Host "[OK] Removed $INSTALL_DIR" -ForegroundColor Green
}

# Remove from PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = ($userPath.Split(";") | Where-Object { $_ -notlike "*\.koda*" }) -join ";"
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")
Write-Host "[OK] Removed from PATH" -ForegroundColor Green

# Remove desktop shortcut
$desktop = [Environment]::GetFolderPath("Desktop")
Remove-Item -Force "$desktop\KODA.lnk" -ErrorAction SilentlyContinue
Write-Host "[OK] Removed desktop shortcut" -ForegroundColor Green

Write-Host "[OK] KODA uninstalled. Config at ~\.config\koda\ was kept." -ForegroundColor Green
