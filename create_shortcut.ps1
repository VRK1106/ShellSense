$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\ShellSense.lnk")

# Point directly to the interface file
$Shortcut.TargetPath = "pythonw.exe" 
$Shortcut.Arguments = """d:\Non_Academic\Project\CommandGenerator\src\shellsense\ui\interface.py"""
$Shortcut.WorkingDirectory = "d:\Non_Academic\Project\CommandGenerator"
$Shortcut.IconLocation = "shell32.dll,24"
$Shortcut.Description = "Launch ShellSense Command Generator"
$Shortcut.Save()

Write-Host "✅ ShellSense shortcut updated on your Desktop!" -ForegroundColor Green
Write-Host "💡 Note: The app will start in the background. Look for the search icon in your System Tray (bottom right)!" -ForegroundColor Cyan
