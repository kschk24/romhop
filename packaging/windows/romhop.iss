; packaging/windows/romhop.iss
; Build: iscc packaging\windows\romhop.iss  (version via env ROMHOP_VERSION)
; Per-user install to %LOCALAPPDATA%\Programs\romhop (no admin -> writable, so
; sub-project 2's self-update needs no elevation).
#define MyVersion GetEnv("ROMHOP_VERSION")

[Setup]
AppName=RomHop
AppVersion={#MyVersion}
AppPublisher=romhop
AppId={{9A469421-551F-4086-B920-5C6C80AB5C9D}
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
; The single romhop.exe also serves the CLI (any args -> Typer). Add {app} to the
; per-user PATH so `romhop <command>` works from a shell (TASK-002).
ChangesEnvironment=yes

[Files]
Source: "..\dist\romhop\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Registry]
; Append {app} to the user PATH (HKCU, no admin). Removed on uninstall.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Icons]
Name: "{group}\RomHop"; Filename: "{app}\romhop.exe"
Name: "{userdesktop}\RomHop"; Filename: "{app}\romhop.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\romhop.exe"; Description: "Launch RomHop"; Flags: nowait postinstall skipifsilent

[Code]
// True when Dir is not already a (semicolon-delimited) entry in the user PATH,
// so the [Registry] append runs at most once across reinstalls.
function NeedsAddPath(Dir: string): Boolean;
var
  Path: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    Path := '';
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Path) + ';') = 0;
end;

// Strip {app} from the user PATH on uninstall, collapsing the leftover ';',
// and offer to wipe config + saved data (opt-in; the ROM library is left
// alone). Mirrors the Linux --uninstall prompt.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path, Dir: string;
  P: Integer;
begin
  if CurUninstallStep <> usUninstall then
    exit;

  // Opt-in wipe of config (%APPDATA%\romhop = platformdirs user_config_dir) and
  // app data (%LOCALAPPDATA%\romhop = user_data_dir: mapping cache, platform
  // names). Default No; the user's downloaded ROM library is never touched.
  if MsgBox('Also remove RomHop''s settings and local cache?' #13#10 #13#10
            'Will delete:' #13#10
            '  - RomHop settings (settings.ini)' #13#10
            '  - RomHop cache (save-to-game mapping, platform names)' #13#10 #13#10
            'Will NOT touch:' #13#10
            '  - Your downloaded ROM library' #13#10
            '  - Your RetroArch save files and savestates',
            mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
  begin
    DelTree(ExpandConstant('{userappdata}\romhop'), True, True, True);
    DelTree(ExpandConstant('{localappdata}\romhop'), True, True, True);
  end;

  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    exit;
  Dir := ExpandConstant('{app}');
  P := Pos(';' + Uppercase(Dir), Uppercase(Path));
  if P = 0 then
    P := Pos(Uppercase(Dir) + ';', Uppercase(Path));
  if P = 0 then
    P := Pos(Uppercase(Dir), Uppercase(Path));
  if P > 0 then
  begin
    Delete(Path, P, Length(Dir));
    StringChangeEx(Path, ';;', ';', True);
    if (Length(Path) > 0) and (Path[1] = ';') then
      Delete(Path, 1, 1);
    if (Length(Path) > 0) and (Path[Length(Path)] = ';') then
      Delete(Path, Length(Path), 1);
    RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path);
  end;
end;
