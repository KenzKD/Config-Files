@echo off
setlocal enabledelayedexpansion

for /f "tokens=2 delims==" %%R in ('findstr /b "ROOT=" "%~f0"') do (
	echo === Root: %%R ===
	if exist "%%R\" call :ScanDir "%%R"
)

echo.
echo Done.
pause
exit /b 0

:ScanDir
set "CURDIR=%~1"
echo Checking: !CURDIR!

if exist "!CURDIR!\.git" (
	echo Found repo: !CURDIR!
	pushd "!CURDIR!"
	git gc --aggressive
	popd
	goto :eof
)

for /d %%D in ("!CURDIR!\*") do (
	call :ScanDir "%%D"
)

goto :eof

ROOT=C:\Users\Lenovo\Desktop\Game_Making
ROOT=C:\Users\Lenovo\Desktop\Coding