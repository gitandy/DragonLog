#!/bin/bash

echo "Get version info..."
VERSION=$(git describe --tags)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then BRANCH=""; fi
STATUS=$(git status -s -uno --porcelain)
if [ -z "$STATUS" ]; then UNCLEAN="False"; else UNCLEAN="True"; fi
echo "__version__ = '$VERSION'" > __version__.py
echo "__branch__ = '$BRANCH'" >> __version__.py
echo "__unclean__ = $UNCLEAN" >> __version__.py
echo "Version: $VERSION $BRANCH $UNCLEAN"

echo Build README...
cp -f README.md README.txt
echo >> README.txt
echo >> README.txt
echo Versions >> README.txt
echo -------- >> README.txt
echo >> README.txt
git tag -n20 --sort=-v:tag >> README.txt

source ./venv/bin/activate

echo
echo "Building Qt files..."
pyuic6 DragonLog_MainWindow.ui -o DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o DragonLog_Settings_ui.py

pylupdate6 DragonLog.py DragonLog_MainWindow.ui DragonLog_QSOForm.ui DragonLog_Settings.ui DragonLog_QSOForm.py DragonLog_Settings.py -ts DragonLog_de.ts
/usr/lib/qt6/bin/lrelease DragonLog_de.ts -qm DragonLog_de.qm

echo
echo "Build executables..."
python setup.py --quiet bdist
sudo ./build_deb.sh $VERSION
echo
echo "...Done!"
