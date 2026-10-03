@echo off
fltmc >nul 2>&1 || (powershell saps wt '\"%~f0\"' -Verb RunAs & exit /b)
winget upgrade --all --include-unknown --accept-package-agreements --accept-source-agreements
pause