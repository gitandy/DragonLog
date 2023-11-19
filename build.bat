@echo off
set PATH=venv\Lib\site-packages\qt6_applications\Qt\bin;%LOCALAPPDATA%\Programs\Git\bin;%ProgramFiles%\Git\bin
set PYTHONPATH=src

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
echo __version__ = '%VERSION%' > src\__version__.py
echo __branch__ = '%BRANCH%' >> src\__version__.py
echo __unclean__ = %UNCLEAN% >> src\__version__.py
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
cd ui_files
pyuic6 DragonLog_MainWindow.ui -o ..\src\DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o ..\src\DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o ..\src\DragonLog_Settings_ui.py
cd ..

pylupdate6 src\DragonLog.py ui_files\DragonLog_MainWindow.ui ui_files\DragonLog_QSOForm.ui ui_files\DragonLog_Settings.ui src\DragonLog_QSOForm.py src\DragonLog_Settings.py -ts i18n\DragonLog_de.ts
mkdir data\i18n
lrelease i18n\DragonLog_de.ts -qm data\i18n\DragonLog_de.qm

echo.
echo Build executables...
python setup.py --quiet bdist
python setup.py --quiet bdist_msi
pause
