[Setup]
AppName=ShellSense
AppVersion=1.0.0
DefaultDirName={pf}\ShellSense
DefaultGroupName=ShellSense
UninstallDisplayIcon={app}\ShellSense.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=ShellSense_Setup_v1.0.0

[Files]
Source: "dist\ShellSense.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ShellSense"; Filename: "{app}\ShellSense.exe"
Name: "{commondesktop}\ShellSense"; Filename: "{app}\ShellSense.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\ShellSense.exe"; Description: "Launch ShellSense"; Flags: nowait postinstall skipifsilent
