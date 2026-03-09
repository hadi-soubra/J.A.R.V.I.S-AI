' J.A.R.V.I.S Launcher — completely silent, no console flash
' Put this file in the same folder as jarvis.pyw

Dim shell
Set shell = CreateObject("WScript.Shell")

' Start Ollama silently
shell.Run "ollama serve", 0, False

' Wait for Ollama to initialize
WScript.Sleep 1500

' Launch with pythonw (no console window)
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
shell.Run "pythonw """ & scriptDir & "jarvis.pyw""", 0, False
