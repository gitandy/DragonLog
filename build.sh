#!/bin/bash

echo "Get version info..."
VERSION=$(git describe --tags)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then BRANCH=""; fi
STATUS=$(git status -s -uno --porcelain)
if [ -z "$STATUS" ]; then UNCLEAN="False"; else UNCLEAN="True"; fi
echo "__version__ = '$VERSION'" > dragonlog/__version__.py
echo "__branch__ = '$BRANCH'" >> dragonlog/__version__.py
echo "__unclean__ = $UNCLEAN" >> dragonlog/__version__.py
echo "Version: $VERSION $BRANCH $UNCLEAN"

export PYTHONPATH=src
source ./venv/bin/activate

echo
echo "Building Qt files..."
cd ui_files
pyuic6 DragonLog_MainWindow.ui -o ../dragonlog/DragonLog_MainWindow_ui.py
pyuic6 DragonLog_QSOForm.ui -o ../dragonlog/DragonLog_QSOForm_ui.py
pyuic6 DragonLog_Settings.ui -o ../dragonlog/DragonLog_Settings_ui.py
cd ..

pylupdate6 dragonlog/DragonLog.py ui_files/DragonLog_MainWindow.ui ui_files/DragonLog_QSOForm.ui ui_files/DragonLog_Settings.ui dragonlog/DragonLog_QSOForm.py dragonlog/DragonLog_Settings.py -ts i18n/DragonLog_de.ts

mkdir -p dragonlog/data/i18n
/usr/lib/qt6/bin/lrelease i18n/DragonLog_de.ts -qm dragonlog/data/i18n/DragonLog_de.qm

echo
echo "Build..."
cp README.md dragonlog/data/README.md
python -m pip install --upgrade pip
python -m pip install --upgrade build
python -m build
echo
echo "...Done!"
