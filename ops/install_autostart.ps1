$ErrorActionPreference = 'Stop'
$aegisRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$launchPath = (Resolve-Path -LiteralPath (Join-Path $aegisRoot 'start_aegis.cmd')).Path
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$aegisTaskName = 'AEGIS-CurrentUser-' + $currentIdentity.User.Value.Split('-')[-1]
$existingTask = Get-ScheduledTask -TaskName $aegisTaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    if ($existingTask.Description -ne 'AEGIS paper research; current-user logon only; no orders') { throw 'Task name belongs to another application' }
    $backupPath = Join-Path $aegisRoot ('research\autostart-backup-' + (Get-Date -Format 'yyyyMMddTHHmmss') + '.xml')
    Export-ScheduledTask -TaskName $aegisTaskName | Set-Content -LiteralPath $backupPath -Encoding UTF8
}
# Keep the supervisor itself as the task's long-lived process. A short-lived
# cmd launcher can leave no healthy service group after the action exits.
$pythonwPath = Join-Path $aegisRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonwPath)) { throw 'Virtual-environment Python unavailable; task unchanged' }
$action = New-ScheduledTaskAction -Execute $pythonwPath -Argument '-m ops.supervisor run' -WorkingDirectory $aegisRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentIdentity.Name
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity.Name -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $aegisTaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'AEGIS paper research; current-user logon only; no orders' -Force | Out-Null
Write-Output ('AUTOSTART_INSTALLED: ' + $aegisTaskName + ' (current user, limited privileges)')
Write-Output 'Keep Windows awake on AC through Settings > System > Power & battery > Screen and sleep. No power settings were changed.'
