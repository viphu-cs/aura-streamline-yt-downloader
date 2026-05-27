@echo off
title Installing Aura Streamline YT Downloader
echo ===================================================
echo   Installing Aura Streamline YT Downloader...
echo ===================================================

set "INSTALL_DIR=%USERPROFILE%\AppData\Local\AuraStreamline"

echo 1. Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 2. Copying application files...
xcopy /E /I /Y "dist\main" "%INSTALL_DIR%" >nul

echo 3. Creating Desktop Shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Aura Streamline YT Downloader.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\main.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\main.exe, 0'; $Shortcut.Save()"

echo 4. Creating Start Menu Shortcut...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\AuraStreamline" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\AuraStreamline"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\AuraStreamline\Aura Streamline YT Downloader.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\main.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\main.exe, 0'; $Shortcut.Save()"

echo ===================================================
echo   Installation Completed Successfully!
echo ===================================================
powershell -Command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); [System.Windows.Forms.MessageBox]::Show('ติดตั้งโปรแกรม Aura Streamline YT Downloader สำเร็จแล้ว!\n\nคุณสามารถเปิดใช้งานแอปพลิเคชันได้ทันทีผ่าน Shortcut บนหน้าจอ Desktop หรือในเมนูเริ่ม (Start Menu) โดยไม่ต้องรันคีย์บอร์ดผ่าน Terminal อีกต่อไปครับ ⚡', 'การติดตั้งเสร็จสมบูรณ์', 0, 64)"

exit
