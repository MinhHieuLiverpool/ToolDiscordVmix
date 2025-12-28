Set oShell = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Dim scriptPath
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
oShell.CurrentDirectory = scriptPath
oShell.Run "pythonw vmix_monitor_gui.py", 0, False
