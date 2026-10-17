param([Parameter(Mandatory=$true)][string]$AppDirectory)
$ErrorActionPreference = 'Stop'
$protectedPrograms = [Environment]::GetFolderPath('ProgramFiles').TrimEnd('\') + '\'
if (-not [IO.Path]::GetFullPath($AppDirectory).StartsWith($protectedPrograms, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'El servicio debe instalarse dentro de Program Files.'
}
$sensorExecutable = Join-Path $AppDirectory 'sensors\COUGARStudioSensors.exe'
if (-not (Test-Path -LiteralPath $sensorExecutable)) { throw 'No se encuentra el lector de sensores.' }
$serviceCommand = '"' + $sensorExecutable + '" --service'
$existingService = Get-Service -Name 'COUGARStudioSensors' -ErrorAction SilentlyContinue
if ($existingService) {
    $serviceRecord = Get-CimInstance Win32_Service -Filter "Name='COUGARStudioSensors'"
    $result = Invoke-CimMethod -InputObject $serviceRecord -MethodName Change -Arguments @{ PathName=$serviceCommand; StartMode='Automatic' }
    if ($result.ReturnValue -ne 0) { throw 'No se pudo actualizar el servicio.' }
} else {
    New-Service -Name COUGARStudioSensors -BinaryPathName $serviceCommand -StartupType Automatic -DisplayName 'COUGAR Studio Sensors' | Out-Null
}
& sc.exe description COUGARStudioSensors 'Lectura local de sensores CPU y GPU para COUGAR Studio. Solo loopback.' | Out-Null
Start-Service -Name COUGARStudioSensors -ErrorAction Stop
