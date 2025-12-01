Set fso      = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' 1. Папка, где лежит .vbs
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)

' 2. main.py
mainScript = """" & scriptFolder & "\main.py" & """"

' 3. Используем pythonw из PATH
pythonw = "pythonw"

' 4. Команда
cmd = pythonw & " " & mainScript

' 5. Запуск
WshShell.Run cmd, 0, False
