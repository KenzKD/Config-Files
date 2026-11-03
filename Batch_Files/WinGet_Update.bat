@echo off
fltmc >nul 2>&1 || (powershell saps wt '\"%~f0\"' -Verb RunAs & exit /b)
powershell -NoProfile -Command "iex ((Get-Content -Raw '%~f0') -split '#PS#')[-1]"
pause & exit /b

#PS#
$start = Get-Date

winget upgrade --all --include-unknown --accept-package-agreements --accept-source-agreements

$folders = "$env:USERPROFILE\Desktop\*", "$env:PUBLIC\Desktop\*"

Get-ChildItem $folders -Include *.lnk, *.url | Where-Object CreationTime -gt $start | Remove-Item -Verbose