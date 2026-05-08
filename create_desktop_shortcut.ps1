# create_desktop_shortcut.ps1
# Run this script once to create a desktop shortcut for TimeCalc

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VbsLauncher  = Join-Path $ProjectDir "TimeCalc.vbs"
$ShortcutPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'TimeCalc.lnk')

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath      = "wscript.exe"
$Shortcut.Arguments       = "`"$VbsLauncher`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description     = "Sheet Times Comparison - TimeCalc"
$Shortcut.IconLocation    = "C:\Windows\System32\imageres.dll,109"   # clock-like icon
$Shortcut.Save()

Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
