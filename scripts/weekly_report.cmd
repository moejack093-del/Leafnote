@echo off
REM Weekly report. Registered as the scheduled task "Leafnote Report".
REM Rewrites REPORT.md from live Etsy data every Monday morning.

cd /d "%~dp0.."
"C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe" scripts\report.py >> "%~dp0..\data\report.log" 2>&1
echo --- %DATE% %TIME% exit=%ERRORLEVEL% >> "%~dp0..\data\report.log"
