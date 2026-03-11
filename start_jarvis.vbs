
' J.A.R.V.I.S Launcher — completely silent, no console flash
' Put this file in the same folder as jarvis.pyw

Dim shell, wmi, process, isRunning
Set shell = CreateObject("WScript.Shell")
Set wmi = GetObject("winmgmts:\\.\root\cimv2")

' Check if jarvis.pyw is already running
isRunning = False
Set process = wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'pythonw.exe'")

For Each p In process
    If InStr(p.CommandLine, "jarvis.pyw") > 0 Then
        isRunning = True
        Exit For
    End If
Next

' Only launch if not already running
If Not isRunning Then
    ' Start Ollama silently
    shell.Run "ollama serve", 0, False
    
    ' Launch J.A.R.V.I.S with pythonw (no console window)
    Dim scriptDir
    scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
    shell.Run "pythonw """ & scriptDir & "jarvis.pyw""", 0, False
End If
