$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force '.deps','licenses' | Out-Null
function Get-VerifiedFile([string]$Uri, [string]$File, [string]$Sha256) {
    if (-not (Test-Path -LiteralPath $File)) { Invoke-WebRequest -Uri $Uri -OutFile $File }
    if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLower() -ne $Sha256) { throw "Hash incorrecto: $File" }
}
Get-VerifiedFile 'https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.6/LibreHardwareMonitor.zip' '.deps\LibreHardwareMonitor.zip' '086d9f1b5a99e643edc2cfaaac16051685b551e4c5ac0b32a57c58c0e529c001'
Get-VerifiedFile 'https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe' '.deps\PawnIO_setup.exe' '1f519a22e47187f70a1379a48ca604981c4fcf694f4e65b734aaa74a9fba3032'
Get-VerifiedFile 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' '.deps\innosetup-6.7.3.exe' '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
foreach ($signedFile in @('.deps\PawnIO_setup.exe','.deps\innosetup-6.7.3.exe')) {
    if ((Get-AuthenticodeSignature -LiteralPath $signedFile).Status -ne 'Valid') { throw "Firma no valida: $signedFile" }
}
Expand-Archive -LiteralPath '.deps\LibreHardwareMonitor.zip' -DestinationPath '.deps\lhm' -Force
$licenseFiles = @{
 'LibreHardwareMonitor-MPL-2.0.txt'='https://raw.githubusercontent.com/LibreHardwareMonitor/LibreHardwareMonitor/v0.9.6/LICENSE';
 'LibreHardwareMonitor-THIRD-PARTY-NOTICES.txt'='https://raw.githubusercontent.com/LibreHardwareMonitor/LibreHardwareMonitor/v0.9.6/THIRD-PARTY-NOTICES.txt';
 'PawnIO-GPL-2.0.txt'='https://raw.githubusercontent.com/namazso/PawnIO/2.2.0/COPYING';
 'PawnIO-exception-and-notices.md'='https://raw.githubusercontent.com/namazso/PawnIO/2.2.0/README.md';
 'Python-PSF.txt'='https://raw.githubusercontent.com/python/cpython/v3.14.0/LICENSE';
 'Tcl-license.txt'='https://raw.githubusercontent.com/tcltk/tcl/core-8-6-branch/license.terms';
 'Tk-license.txt'='https://raw.githubusercontent.com/tcltk/tk/core-8-6-branch/license.terms';
 'Microsoft-dotnet-MIT.txt'='https://raw.githubusercontent.com/dotnet/runtime/v10.0.2/LICENSE.TXT'
}
foreach ($name in $licenseFiles.Keys) {
    $destination = Join-Path 'licenses' $name
    if (-not (Test-Path -LiteralPath $destination)) { Invoke-WebRequest -Uri $licenseFiles[$name] -OutFile $destination }
}
