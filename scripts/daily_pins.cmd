@echo off
REM Daily Pinterest drip. Registered as the scheduled task "Leafnote Pins".
REM
REM Pacing matters more than volume here: Pinterest throttles accounts that
REM publish in bursts, and the queue is finite anyway. 8/day works through
REM the backlog in about three weeks while looking like a person posting.
REM
REM post_pins.py keys off data/pins_posted.json, so a missed day costs
REM nothing and a double run never duplicates a pin.

cd /d "%~dp0.."
"C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe" scripts\post_pins.py --live --limit 8 >> "%~dp0..\data\pin_drip.log" 2>&1
echo --- %DATE% %TIME% exit=%ERRORLEVEL% >> "%~dp0..\data\pin_drip.log"
