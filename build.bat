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
echo __version__ = '%VERSION%' > dragonlog\__version__.py
echo __branch__ = '%BRANCH%' >> dragonlog\__version__.py
echo __unclean__ = %UNCLEAN% >> dragonlog\__version__.py
echo Version: %VERSION% %BRANCH% %UNCLEAN%
del version.txt branch.txt status.txt

echo Building Qt files...
cd ui_files
pyuic6 DragonLog_MainWindow.ui -o ..\dragonlog\DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o ..\dragonlog\DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o ..\dragonlog\DragonLog_Settings_ui.py
pyuic6 DragonLog_AppSelect.ui -o ..\dragonlog\DragonLog_AppSelect_ui.py
cd ..

pylupdate6 dragonlog\DragonLog.py ui_files\DragonLog_MainWindow.ui ui_files\DragonLog_QSOForm.ui ui_files\DragonLog_Settings.ui ui_files\DragonLog_AppSelect.ui dragonlog\DragonLog_QSOForm.py dragonlog\DragonLog_Settings.py dragonlog\DragonLog_AppSelect.py dragonlog\DragonLog_eQSL.py dragonlog\DragonLog_LoTW.py dragonlog\DragonLog_CallBook.py -ts i18n\DragonLog_de.ts
mkdir dragonlog\data\i18n
lrelease i18n\DragonLog_de.ts -qm dragonlog\data\i18n\DragonLog_de.qm
copy i18n\*.json dragonlog\data\i18n\

echo.
echo Build...
copy README.md dragonlog\data\README.md
python setup_msi.py bdist -d dist_exe bdist_msi -d dist_exe
python -m pip install --upgrade pip
python -m pip install --upgrade build
python -m build
pause
