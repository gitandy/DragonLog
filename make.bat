@echo off
set PATH=C:\cygwin64\bin;C:\cygwin64\lib\qt5\bin;venv\Lib\site-packages\qt6_applications\Qt\bin;
SET PROJ_PATH=%~dp0

call %PROJ_PATH%venv\Scripts\activate.bat

echo Invoking make %* ...
make.exe %*
