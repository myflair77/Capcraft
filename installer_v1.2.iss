[Setup]
AppId={{01234567-89AB-CDEF-0123-456789ABCDEF}
AppName=Capcraft
AppVersion=1.2
AppPublisher=JBH
DefaultDirName={autopf}\Capcraft
DefaultGroupName=Capcraft
OutputDir=dist\Installer
OutputBaseFilename=Capcraft_Setup_v1.2
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Capcraft v1.2.exe
CloseApplications=yes

[InstallDelete]
Type: filesandordirs; Name: "{app}\*"

[Files]
Source: "dist\Capcraft v1.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Capcraft"; Filename: "{app}\Capcraft v1.2.exe"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\Capcraft"; Filename: "{app}\Capcraft v1.2.exe"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{sys}\attrib.exe"; Parameters: "+h ""{app}\_internal\guide.html"""; Flags: runhidden skipifdoesntexist
Filename: "{sys}\attrib.exe"; Parameters: "+h ""{app}\guide.html"""; Flags: runhidden skipifdoesntexist
Filename: "{app}\Capcraft v1.2.exe"; Description: "{cm:LaunchProgram,Capcraft}"; Flags: nowait postinstall skipifsilent
