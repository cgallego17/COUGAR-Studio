param([string]$AppVersion='0.1.0', [string]$Python='python', [string]$InnoCompiler='')
$ErrorActionPreference = 'Stop'
$buildRoot = $PSScriptRoot
Set-Location -LiteralPath $buildRoot
if ($AppVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Version no valida' }
& "$buildRoot\prepare-dependencies.ps1"
if (-not $InnoCompiler) { $InnoCompiler = "$buildRoot\.deps\inno\ISCC.exe" }
if (-not (Test-Path -LiteralPath $InnoCompiler)) {
    $compilerSetup = Start-Process -FilePath "$buildRoot\.deps\innosetup-6.7.3.exe" -ArgumentList ('/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /NOICONS /DIR="'+$buildRoot+'\.deps\inno"') -WindowStyle Hidden -Wait -PassThru
    if ($compilerSetup.ExitCode -ne 0) { throw 'No se pudo preparar Inno Setup' }
}
@("VERSION = '$AppVersion'", "REPOSITORY = 'cgallego17/COUGAR-Studio'") | Set-Content -LiteralPath 'app_version.py' -Encoding UTF8
New-Item -ItemType Directory -Force 'sensors\bin','release' | Out-Null
Copy-Item -Path '.deps\lhm\*.dll' -Destination 'sensors\bin' -Force
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:exe /platform:x64 /optimize+ /out:sensors\bin\COUGARStudioSensors.exe /reference:.deps\lhm\LibreHardwareMonitorLib.dll /reference:System.Web.Extensions.dll /reference:System.ServiceProcess.dll sensors\SensorService.cs
if ($LASTEXITCODE -ne 0) { throw 'Error al compilar el servicio' }
& $Python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas' }
& $Python build_catalog.py
if ($LASTEXITCODE -ne 0) { throw 'Error al generar el catalogo' }
Copy-Item -LiteralPath 'catalogo-animaciones-y-letras.html' -Destination 'assets\catalogo-animaciones-y-letras.html' -Force
& $Python -m PyInstaller --noconfirm --clean 'COUGAR Studio.spec'
if ($LASTEXITCODE -ne 0) { throw 'Error al empaquetar la aplicacion' }
$exeTest = Start-Process -FilePath '.\dist\COUGAR Studio\COUGAR Studio.exe' -ArgumentList '--smoke-test' -WindowStyle Hidden -Wait -PassThru
if ($exeTest.ExitCode -ne 0) { throw 'Error al comprobar el ejecutable' }
& $InnoCompiler "/DAppVersion=$AppVersion" 'installer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Error al generar el instalador' }
& $Python package-sources.py
if ($LASTEXITCODE -ne 0) { throw 'Error al preparar fuentes de terceros' }
Get-ChildItem -LiteralPath 'release' -File | Where-Object Name -ne 'SHA256SUMS.txt' | ForEach-Object {
    ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()+'  '+$_.Name)
} | Set-Content -LiteralPath 'release\SHA256SUMS.txt' -Encoding ASCII
