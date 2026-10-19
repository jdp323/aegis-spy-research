$ErrorActionPreference = 'Stop'
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$aegisTaskName = 'AEGIS-CurrentUser-' + $currentIdentity.User.Value.Split('-')[-1]
$task = Get-ScheduledTask -TaskName $aegisTaskName -ErrorAction SilentlyContinue
if ($task) {
    if ($task.Description -ne 'AEGIS paper research; current-user logon only; no orders') { throw 'Task belongs to another application' }
    $aegisRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    Export-ScheduledTask -TaskName $aegisTaskName | Set-Content -LiteralPath (Join-Path $aegisRoot ('research\autostart-uninstall-' + (Get-Date -Format 'yyyyMMddTHHmmss') + '.xml')) -Encoding UTF8
    Unregister-ScheduledTask -TaskName $aegisTaskName -Confirm:$false
}
Write-Output 'AEGIS current-user logon autostart removed; project and records retained.'
