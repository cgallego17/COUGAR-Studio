$ErrorActionPreference = 'Stop'
$studioService = Get-Service -Name 'COUGARStudioSensors' -ErrorAction SilentlyContinue
if ($studioService -and $studioService.Status -ne 'Stopped') {
    Stop-Service -Name 'COUGARStudioSensors' -ErrorAction Stop
    $studioService.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
}
