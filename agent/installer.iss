; Inno Setup Script for InfraMind AI Windows Agent
; Generates InfraMindAgentSetup.exe installer with Start Menu, Desktop shortcuts, and Windows Autostart.

#define MyAppName "InfraMind AI Windows Agent"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "InfraMind AI Team"
#define MyAppURL "https://inframind-ai-three.vercel.app"
#define MyAppExeName "InfraMindAgent.exe"

[Setup]
AppId={{D41A2E3B-9981-4C41-9E28-8977F322D88C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\InfraMindAI\Agent
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\README.md
OutputDir=dist
OutputBaseFilename=InfraMindAgentSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Automatically start InfraMind Agent when Windows logs in"; GroupDescription: "Startup Options:"

[Files]
Source: "dist\InfraMindAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "InfraMindAgent"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
