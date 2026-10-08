$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$StartupPath = [Environment]::GetFolderPath('Startup')

# Desktop Shortcut
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\ShellSense.lnk")
$Shortcut.TargetPath = "pythonw.exe" 
$Shortcut.Arguments = """d:\Non_Academic\Project\CommandGenerator\src\shellsense\ui\interface.py"""
$Shortcut.WorkingDirectory = "d:\Non_Academic\Project\CommandGenerator"
$Shortcut.IconLocation = "shell32.dll,24"
$Shortcut.Description = "Launch ShellSense Command Generator"
$Shortcut.Save()

# Startup Shortcut
$StartupShortcut = $WshShell.CreateShortcut("$StartupPath\ShellSense.lnk")
$StartupShortcut.TargetPath = "pythonw.exe" 
$StartupShortcut.Arguments = """d:\Non_Academic\Project\CommandGenerator\src\shellsense\ui\interface.py"""
$StartupShortcut.WorkingDirectory = "d:\Non_Academic\Project\CommandGenerator"
$StartupShortcut.IconLocation = "shell32.dll,24"
$StartupShortcut.Description = "Launch ShellSense Command Generator"
$StartupShortcut.Save()

Write-Host "✅ ShellSense shortcut updated on your Desktop!" -ForegroundColor Green
Write-Host "✅ ShellSense added to system startup!" -ForegroundColor Green
Write-Host "💡 Note: The app will start in the background. Look for the search icon in your System Tray (bottom right)!" -ForegroundColor Cyan
