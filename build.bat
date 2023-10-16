@echo off
set PATH=venv\Lib\site-packages\qt6_applications\Qt\bin;%LOCALAPPDATA%\Programs\Git\bin;%ProgramFiles%\Git\bin

call venv\Scripts\activate.bat

::echo "Installing requirements..."
::pip3 install -r requirements.txt

echo Get version info...
git describe --tags > version.txt
set /p VERSION=<version.txt
git rev-parse --abbrev-ref HEAD > branch.txt
set /p BRANCH=<branch.txt
if "%BRANCH%" EQU "master" set BRANCH=
git status -s -uno --porcelain > status.txt
FOR %%I in (status.txt) do set STAT_SIZE=%%~zI
if %STAT_SIZE% GTR 0 (set UNCLEAN=True) else (set UNCLEAN=False)
echo __version__ = '%VERSION%' > __version__.py
echo __branch__ = '%BRANCH%' >> __version__.py
echo __unclean__ = %UNCLEAN% >> __version__.py
echo Version: %VERSION% %BRANCH% %UNCLEAN%
del version.txt branch.txt status.txt

echo Build README...
copy README.md README.txt
echo. >> README.txt
echo. >> README.txt
echo Versions >> README.txt
echo -------- >> README.txt
echo. >> README.txt
git tag -n20 --sort=-v:tag >> README.txt

echo Building Qt files...
pyuic6 DragonLog_MainWindow.ui -o DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o DragonLog_Settings_ui.py

pylupdate6 DragonLog.py DragonLog_MainWindow.ui DragonLog_QSOForm.ui DragonLog_Settings.ui DragonLog_QSOForm.py DragonLog_Settings.py -ts DragonLog_de.ts
lrelease DragonLog_de.ts -qm DragonLog_de.qm

echo.
echo Build executables...
python setup.py --quiet bdist
python setup.py --quiet bdist_msi
pause
