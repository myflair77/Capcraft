[Setup]
AppId={{01234567-89AB-CDEF-0123-456789ABCDEF}
AppName=Capcraft
AppVersion=1.2.0
AppVerName=Capcraft 1.2
AppPublisher=JBH
DefaultDirName={autopf}\Capcraft
DefaultGroupName=Capcraft
OutputDir=dist-dev\Installer
OutputBaseFilename=Capcraft_Setup_v1.2.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppPublisherURL=https://github.com/myflair77/Capcraft
AppUpdatesURL=https://github.com/myflair77/Capcraft/releases
Compression=lzma2/normal
SolidCompression=yes
SetupIconFile=build\release-resources\icon.ico
LicenseFile=LICENSE
UninstallDisplayIcon={app}\Capcraft v1.2.exe
CloseApplications=yes

[Files]
Source: "dist-dev\Capcraft v1.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\release-resources\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Capcraft"; Filename: "{app}\Capcraft v1.2.exe"; IconFilename: "{app}\icon.ico"; AppUserModelID: "JBH.Capcraft"
Name: "{autodesktop}\Capcraft"; Filename: "{app}\Capcraft v1.2.exe"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"; AppUserModelID: "JBH.Capcraft"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Remove only loose guide files left by an older installation in this app dir.
Type: files; Name: "{app}\guide.html"
Type: files; Name: "{app}\_internal\guide.html"

[Run]
Filename: "{app}\Capcraft v1.2.exe"; Description: "{cm:LaunchProgram,Capcraft}"; Flags: nowait postinstall skipifsilent
