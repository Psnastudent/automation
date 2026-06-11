"""
Windows Task Scheduler Setup
Registers the automation as a Windows Scheduled Task
so it survives reboots and runs automatically.
"""

import os
import sys
import subprocess
from pathlib import Path

TASK_NAME = "LeetCodeDailyAutomation"
SCRIPT_DIR = Path(__file__).parent.resolve()
MAIN_SCRIPT = SCRIPT_DIR / "main.py"
PYTHON_EXE = sys.executable


def register_windows_task():
    """Register the automation as a Windows Scheduled Task."""
    print("🔧 Setting up Windows Task Scheduler...")

    # Build the action command
    command = f'"{PYTHON_EXE}" "{MAIN_SCRIPT}"'
    working_dir = str(SCRIPT_DIR)

    # XML Task definition
    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>LeetCode Daily Problem Automation - Solves 5 problems every day and sends email report</Description>
    <Author>LeetCode Automation</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T08:00:00</StartBoundary>
      <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
    <BootTrigger>
      <Enabled>false</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <WakeToRun>false</WakeToRun>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_EXE}</Command>
      <Arguments>"{MAIN_SCRIPT}"</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # Save task XML
    xml_path = SCRIPT_DIR / "task_schedule.xml"
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    # Register with Task Scheduler
    try:
        result = subprocess.run(
            [
                "schtasks", "/Create",
                "/TN", TASK_NAME,
                "/XML", str(xml_path),
                "/F"
            ],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ Task '{TASK_NAME}' registered successfully!")
            print(f"   ➤ Will run daily at 08:00 AM")
            print(f"   ➤ Task Manager → Task Scheduler Library → {TASK_NAME}")
        else:
            print(f"❌ Task registration failed: {result.stderr}")
            print(f"   Try running this script as Administrator")
    except FileNotFoundError:
        print("❌ schtasks not found. Please run this on Windows.")
    finally:
        if xml_path.exists():
            xml_path.unlink()


def unregister_windows_task():
    """Remove the scheduled task."""
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ Task '{TASK_NAME}' removed successfully")
        else:
            print(f"⚠️ Could not remove task: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unregister":
        unregister_windows_task()
    else:
        register_windows_task()
