@echo off
set PATH=venv\Lib\site-packages\qt6_applications\Qt\bin;%LOCALAPPDATA%\Programs\Git\bin
::set PYTHONPATH=..\pymdstg

call venv\Scripts\activate.bat

::echo "Installing requirements..."
::pip3 install -r requirements.txt

REM echo Get version info...
REM git describe --tags > version.txt
REM set /p VERSION=<version.txt
REM git rev-parse --abbrev-ref HEAD > branch.txt
REM set /p BRANCH=<branch.txt
REM if "%BRANCH%" EQU "master" set BRANCH=
REM git status -s -uno --porcelain > status.txt
REM FOR %%I in (status.txt) do set STAT_SIZE=%%~zI
REM if %STAT_SIZE% GTR 0 (set UNCLEAN=True) else (set UNCLEAN=False)
REM echo __version__ = '%VERSION%' > __version__.py
REM echo __branch__ = '%BRANCH%' >> __version__.py
REM echo __unclean__ = %UNCLEAN% >> __version__.py
REM echo Version: %VERSION% %BRANCH% %UNCLEAN%
REM del version.txt branch.txt status.txt

REM echo Build README...
REM copy README.md README.txt
REM echo. >> README.txt
REM echo. >> README.txt
REM echo Versions >> README.txt
REM echo -------- >> README.txt
REM echo. >> README.txt
REM git tag -n20 --sort=-v:tag >> README.txt

echo Building Qt files...
pyuic6 DragonLog_MainWindow.ui -o DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o DragonLog_Settings_ui.py

pylupdate6 DragonLog.py DragonLog_MainWindow.ui DragonLog_QSOForm.ui DragonLog_Settings.ui -ts DragonLog_de.ts
lrelease DragonLog_de.ts -qm DragonLog_de.qm

echo.
echo Build executables...
python setup.py --quiet bdist
python setup.py --quiet bdist_msi
pause
