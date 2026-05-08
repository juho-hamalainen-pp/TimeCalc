Dim oShell
Set oShell = CreateObject("WScript.Shell")

Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

Dim pythonScript
pythonScript = scriptDir & "sheet_times_comparison.py"

' Run Python without showing a console window (0 = hidden)
oShell.Run "python """ & pythonScript & """", 0, False

Set oShell = Nothing
