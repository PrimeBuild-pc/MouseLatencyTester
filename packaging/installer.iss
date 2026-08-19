; Inno Setup script for the Latency Tester Windows installer.
;
; Build with:  packaging\build_installer.ps1
; It expects the PyInstaller one-folder output in build\dist\LatencyTester.
;
; The installed directory deliberately contains the firmware sketches and the
; documentation next to the executable, so a user who installs the app has
; everything needed to flash the Teensy without going back to the repository.

#define AppName        "Latency Tester"
#ifndef AppVersion
  #define AppVersion   "3.0.0"
#endif
#define AppPublisher   "PrimeBuild"
#define AppURL         "https://github.com/PrimeBuild-pc/MouseLatencyTester"
#define AppExeName     "LatencyTester.exe"
#define SourceDir      "..\build\dist\LatencyTester"
#define RepoRoot       ".."

[Setup]
AppId={{7B4E2C31-9A6D-4F58-B0C7-2E5A8D913F44}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile={#RepoRoot}\LICENSE
InfoAfterFile={#RepoRoot}\packaging\after_install.txt

; Per-user install by default so no admin prompt is needed; the user can still
; choose an all-users install from the privileges dialog.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir={#RepoRoot}\build\installer
OutputBaseFilename=LatencyTester-{#AppVersion}-Setup
SetupIconFile={#RepoRoot}\packaging\app.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
AllowNoIcons=yes

[Languages]
; The application itself ships eight languages (including Chinese, which Inno
; Setup has no official translation for); the installer wizard uses the seven
; that are available and falls back to English otherwise.
Name: "english";  MessagesFile: "compiler:Default.isl"
Name: "italian";  MessagesFile: "compiler:Languages\Italian.isl"
Name: "german";   MessagesFile: "compiler:Languages\German.isl"
Name: "french";   MessagesFile: "compiler:Languages\French.isl"
Name: "spanish";  MessagesFile: "compiler:Languages\Spanish.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "russian";  MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Application (PyInstaller one-folder output).
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*";   DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Firmware sketches — installed alongside the app so the Teensy can be flashed
; without cloning the repository.
Source: "{#RepoRoot}\firmware\*"; DestDir: "{app}\firmware"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation.
Source: "{#RepoRoot}\docs\*";      DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\README.md";    DestDir: "{app}"; Flags: ignoreversion
Source: "{#RepoRoot}\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RepoRoot}\LICENSE";      DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExeName}"
Name: "{group}\Firmware sketches";     Filename: "{app}\firmware"
Name: "{group}\Documentation";         Filename: "{app}\docs"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Only build artefacts the app itself writes inside its own directory.
; The measurement archive lives in the user's Documents folder and is
; deliberately NEVER touched by the uninstaller.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"

[Messages]
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%nThe firmware sketches and the full documentation are installed alongside the application, so you can flash the Teensy straight from the installed folder.%n%nYour measurement archive is stored separately in your Documents folder and is never removed by the uninstaller.
