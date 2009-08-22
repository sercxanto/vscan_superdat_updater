@echo off
set dir=\\server\vscanupd\sdat
for /f %%i in ('dir /oN /b %dir%') do @set latest=%%i

set filePath=%dir%\%latest%
echo Found %filePath%, starting...
REM Under Windows XP's system account %TEMP% is usually under C:\WINDOWS\TEMP
start /wait %filePath% /silent /LOGFILE %temp%\startLatestSuperdat_log.txt
echo Finished with error code %ERRORLEVEL%
exit %ERRORLEVEL%
