[Setup]
AppName=Capcraft
AppVersion=1.1
AppPublisher=JBH
DefaultDirName={autopf}\Capcraft
DefaultGroupName=Capcraft
OutputDir=dist\Installer
OutputBaseFilename=Capcraft_Setup_v1.1
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Capcraft v1.1.exe

[Files]
Source: "dist\Capcraft v1.1\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Capcraft"; Filename: "{app}\Capcraft v1.1.exe"
Name: "{autodesktop}\Capcraft"; Filename: "{app}\Capcraft v1.1.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\Capcraft v1.1.exe"; Description: "{cm:LaunchProgram,Capcraft}"; Flags: nowait postinstall skipifsilent
