$ErrorActionPreference = 'Stop'
$service = Get-Service -Name 'COUGARStudioSensors' -ErrorAction SilentlyContinue
if ($service) {
    Restart-Service -Name 'COUGARStudioSensors' -ErrorAction Stop
} else {
    $fallbackService = Get-Service -Name 'RM-Hardware' -ErrorAction SilentlyContinue
    if ($fallbackService) { Restart-Service -Name 'RM-Hardware' -ErrorAction Stop }
}
