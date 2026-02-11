' Silent launcher for AI Brief Scheduler
' Uses WScript.Shell with window style 0 (hidden) — no black window at all
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\conta\OneDrive\Projects\catfun"
WshShell.Run """C:\ProgramData\anaconda3\pythonw.exe"" -m aibrief.scheduler", 0, False
