# Setting Up VISTA3D Service to Run on Startup

This guide will help you configure the VISTA3D service to automatically start when your computer boots up.

## Option 1: Using Windows Task Scheduler (Recommended)

### Step 1: Test the Batch File

1. First, test the batch file by double-clicking `start_vista_service.bat`
2. Check that the service starts correctly
3. Verify that log files are created in the VISTA directory

### Step 2: Create a Task in Task Scheduler

1. Press `Win + R`, type `taskschd.msc` and press Enter
2. In Task Scheduler, click on "Create Basic Task..." in the right panel
3. Enter a name (e.g., "VISTA3D Service") and description, then click Next
4. Select "When the computer starts" as the trigger, then click Next
5. Select "Start a program" as the action, then click Next
6. Browse to select `C:\Users\Albert\VISTA\start_vista_service.bat` as the program/script
7. Set "Start in" to `C:\Users\Albert\VISTA`, then click Next
8. Check "Open the Properties dialog for this task when I click Finish"
9. Click Finish

### Step 3: Configure Advanced Settings

In the Properties dialog that opens:
1. Go to the "General" tab
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
2. Go to the "Conditions" tab
   - Uncheck "Start the task only if the computer is on AC power"
3. Go to the "Settings" tab
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
4. Click OK and enter your Windows password when prompted

## Option 2: Using NSSM (Non-Sucking Service Manager)

For a more robust Windows service setup:

### Step 1: Download and Install NSSM

1. Download NSSM from [nssm.cc](https://nssm.cc/download)
2. Extract the ZIP file
3. Copy `nssm.exe` (from the appropriate architecture folder) to `C:\Windows\System32`

### Step 2: Create a Windows Service

1. Open Command Prompt as Administrator
2. Run the following command:
   ```
   nssm install VISTA3D_Service
   ```
3. In the NSSM dialog:
   - Path: `C:\Users\Albert\AppData\Local\Programs\Python\Python313\python.exe` (adjust path to your Python)
   - Startup directory: `C:\Users\Albert\VISTA`
   - Arguments: `vista_service.py --base_dir C:\Users\Albert\vista_service --interval 30`
4. Go to the "Details" tab:
   - Display name: VISTA3D Service
   - Description: VISTA3D Medical Image Segmentation Service
5. Go to the "Log on" tab:
   - Select "Local System account"
6. Click "Install service"

### Step 3: Start the Service

1. Open Services (services.msc)
2. Find "VISTA3D_Service" in the list
3. Right-click and select "Start"
4. Set startup type to "Automatic"

## Verifying the Service is Running

1. Check the log files:
   - `C:\Users\Albert\VISTA\service_startup.log`
   - `C:\Users\Albert\VISTA\service_output.log`
   - `C:\Users\Albert\VISTA\vista_service.log`

2. Create a test task:
   ```
   python create_task.py --input "C:\path\to\ct.nii.gz" --output "C:\path\to\output" --type "full"
   ```

3. Check if the task is processed by looking in the `processed` folder

## Troubleshooting

If the service doesn't start:

1. Check Windows Event Viewer for errors
2. Verify Python path in the batch file
3. Make sure all required Python packages are installed
4. Check that the VISTA3D code is accessible to the service account

## Stopping the Service

### Task Scheduler Method
1. Open Task Scheduler
2. Find your task
3. Right-click and select "End"

### NSSM Method
1. Open Command Prompt as Administrator
2. Run: `nssm stop VISTA3D_Service`
3. To remove the service: `nssm remove VISTA3D_Service confirm`
