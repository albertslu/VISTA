# PowerShell script to update the Vista3D Service scheduled task to run with administrator privileges
# This script must be run with administrator privileges

# Unregister the existing task if it exists
$taskName = "Vista3D Service"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($taskExists) {
    Write-Host "Unregistering existing Vista3D Service task..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create a new task with administrator privileges
$action = New-ScheduledTaskAction -Execute "C:\Users\Albert\VISTA\start_vista_service.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Register the new task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Automatically starts the VISTA3D medical image segmentation service with administrator privileges"

Write-Host "Vista3D Service task has been updated to run with administrator privileges at system startup."
Write-Host "To start the service now, run: Start-ScheduledTask -TaskName 'Vista3D Service'"
