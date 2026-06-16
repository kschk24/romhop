; packaging/windows/romhop.iss
; Build: iscc packaging\windows\romhop.iss  (version via env ROMHOP_VERSION)
; Per-user install to %LOCALAPPDATA%\Programs\romhop (no admin -> writable, so
; sub-project 2's self-update needs no elevation).
#define MyVersion GetEnv("ROMHOP_VERSION")

[Setup]
AppName=RomHop
AppVersion={#MyVersion}
AppPublisher=romhop
DefaultDirName={localappdata}\Programs\romhop
DefaultGroupName=RomHop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
; Paths below are relative to this .iss file (packaging\windows\). PyInstaller
; writes to packaging\dist\ (it is run from packaging\), i.e. ..\dist here.
OutputDir=..\dist
OutputBaseFilename=romhop-setup-{#MyVersion}
UninstallDisplayIcon={app}\romhop.exe
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\romhop\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\RomHop"; Filename: "{app}\romhop.exe"
Name: "{userdesktop}\RomHop"; Filename: "{app}\romhop.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\romhop.exe"; Description: "Launch RomHop"; Flags: nowait postinstall skipifsilent
