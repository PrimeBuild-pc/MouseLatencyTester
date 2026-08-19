<#
.SYNOPSIS
    Builds the Latency Tester Windows installer.

.DESCRIPTION
    Runs the test suite, freezes the app with PyInstaller (one-folder), then
    compiles the Inno Setup script.  The resulting installer places the app,
    the firmware sketches and the documentation in a single folder.

    Output:  build\installer\LatencyTester-<version>-Setup.exe

.PARAMETER SkipTests
    Skip pytest.  Only for iterating on packaging itself; never for a release.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "Latency Tester -- installer build" -ForegroundColor Cyan
Write-Host "repository: $repo"

# --- prerequisites --------------------------------------------------------
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { throw "python was not found on PATH." }

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php"
}

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install --quiet pyinstaller
}

# Keep the shipped version numbers in one place: read it from the package.
$version = python -c "import latency_tester; print(latency_tester.__version__)"
Write-Host "version:    $version"

# --- tests ----------------------------------------------------------------
if ($SkipTests) {
    Write-Warning "tests skipped -- do not ship this build"
} else {
    Write-Host "`n[1/3] running tests" -ForegroundColor Cyan
    python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw "tests failed; build aborted." }
}

# --- freeze ---------------------------------------------------------------
Write-Host "`n[2/3] freezing with PyInstaller" -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean `
    --distpath build\dist --workpath build\work `
    packaging\LatencyTester.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

$exe = "build\dist\LatencyTester\LatencyTester.exe"
if (-not (Test-Path $exe)) { throw "expected $exe to exist." }

# The locale files are data, not imports: verify they actually made it in.
$locales = Get-ChildItem "build\dist\LatencyTester\_internal\latency_tester\locales\*.json" -ErrorAction SilentlyContinue
if ($locales.Count -lt 8) {
    throw "only $($locales.Count) locale files were bundled; expected 8."
}
Write-Host "bundled locales: $($locales.Count)"

# --- installer ------------------------------------------------------------
Write-Host "`n[3/3] compiling the installer" -ForegroundColor Cyan
& $iscc "/DAppVersion=$version" packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed." }

$setup = Get-Item "build\installer\LatencyTester-$version-Setup.exe"
$sizeMb = [math]::Round($setup.Length / 1MB, 1)

# A checksum users can verify against the release page.
$hash = (Get-FileHash $setup.FullName -Algorithm SHA256).Hash
"$hash  $($setup.Name)" | Set-Content "$($setup.DirectoryName)\SHA256SUMS.txt" -Encoding ascii

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  $($setup.FullName)  ($sizeMb MB)"
Write-Host "  SHA256: $hash"
