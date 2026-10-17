#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
[Setup]
AppId={{7D51BC77-6CC1-46E7-974B-F0F6532CA404}
AppName=COUGAR Studio
AppVersion={#AppVersion}
AppPublisher=cgallego17
AppPublisherURL=https://github.com/cgallego17/COUGAR-Studio
AppUpdatesURL=https://github.com/cgallego17/COUGAR-Studio/releases
DefaultDirName={autopf}\COUGAR Studio
DefaultGroupName=COUGAR Studio
OutputDir=release
OutputBaseFilename=COUGAR-Studio-Setup-{#AppVersion}-x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
PrivilegesRequired=admin
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
DisableDirPage=yes
LicenseFile=LICENSE
UninstallDisplayIcon={app}\COUGAR Studio.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\COUGAR Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "sensors\bin\*"; DestDir: "{app}\sensors"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "sensors\install-service.ps1"; DestDir: "{app}\sensors"; Flags: ignoreversion
Source: "assets\stop-service.ps1"; DestDir: "{app}\sensors"; Flags: ignoreversion
Source: ".deps\PawnIO_setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\COUGAR Studio"; Filename: "{app}\COUGAR Studio.exe"
Name: "{autodesktop}\COUGAR Studio"; Filename: "{app}\COUGAR Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\COUGAR Studio.exe"; Description: "Abrir COUGAR Studio"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\sensors\stop-service.ps1"""; Flags: runhidden waituntilterminated; RunOnceId: "StopStudioSensors"
Filename: "{sys}\sc.exe"; Parameters: "delete COUGARStudioSensors"; Flags: runhidden waituntilterminated; RunOnceId: "DeleteStudioSensors"

[Code]
var DriverRestart: Boolean;
function PawnIOReady(): Boolean;
var Version: String;
begin
  Result := False;
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO', 'DisplayVersion', Version) then
    Result := StrToIntDef(Copy(Version, 1, Pos('.', Version)-1), 0) >= 2;
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
var Code: Integer;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\sensors\stop-service.ps1')) then
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "'+ExpandConstant('{app}\sensors\stop-service.ps1')+'"',
      '', SW_HIDE, ewWaitUntilTerminated, Code) then Result := 'No se pudo detener el servicio de sensores.';
end;
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer;
begin
  if CurStep = ssPostInstall then begin
    if not PawnIOReady() then begin
      if not Exec(ExpandConstant('{tmp}\PawnIO_setup.exe'), '-install -silent', '', SW_HIDE, ewWaitUntilTerminated, Code) then
        RaiseException('No se pudo iniciar la instalación de PawnIO.');
      if (Code <> 0) and (Code <> 3010) then RaiseException('PawnIO devolvió el código '+IntToStr(Code));
      DriverRestart := Code = 3010;
    end;
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "'+ExpandConstant('{app}\sensors\install-service.ps1')+'" -AppDirectory "'+ExpandConstant('{app}')+'"',
      '', SW_HIDE, ewWaitUntilTerminated, Code) then RaiseException('No se pudo registrar el servicio de sensores.');
    if Code <> 0 then RaiseException('El servicio de sensores devolvió el código '+IntToStr(Code));
  end;
end;
function NeedRestart(): Boolean;
begin Result := DriverRestart; end;
