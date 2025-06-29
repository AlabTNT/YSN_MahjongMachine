@echo off
setlocal enabledelayedexpansion

set version=%1
shift
set description=%1
shift

:loop
if "%1"=="" goto continue
set description=%description% %1
shift
goto loop

:continue

git add .
git commit -m "%version%" -m "%description%"

git push origin main -f
