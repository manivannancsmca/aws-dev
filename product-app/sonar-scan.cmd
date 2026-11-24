@echo off
rem ---------------------------------------------------------------------------
rem sonar-scan.cmd - tests + coverage + SonarQube analysis for product-app.
rem
rem Reads SONAR_TOKEN from the .env file next to this script, so the token
rem belongs to this project only. Works in PowerShell and in cmd:
rem     .\sonar-scan.cmd                -> mvn clean verify sonar:sonar
rem     .\sonar-scan.cmd sonar:sonar    -> any Maven arguments you pass instead
rem
rem The token is handed to Maven as an environment variable that exists only
rem while this script runs (setlocal). It is never put on the Maven command
rem line, where other programs could see it in the process list.
rem ---------------------------------------------------------------------------
setlocal

rem Work in the folder this script lives in (product-app), wherever it is called from
cd /d "%~dp0"

rem 1. Read the line SONAR_TOKEN=... from .env (no spaces around "=").
rem    An empty value is skipped, so a SONAR_TOKEN set in Windows still works.
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="SONAR_TOKEN" if not "%%~B"=="" set "SONAR_TOKEN=%%~B"
  )
)

rem 2. Stop with a clear message when there is no token at all
if not defined SONAR_TOKEN (
  echo ERROR: SONAR_TOKEN is empty. Paste your token into "%~dp0.env" as SONAR_TOKEN=sqa_...
  exit /b 1
)

rem 3. Run Maven: the default goals, or the arguments you passed
if "%~1"=="" (
  call mvn clean verify sonar:sonar
) else (
  call mvn %*
)
exit /b %ERRORLEVEL%
