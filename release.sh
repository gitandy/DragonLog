#!/bin/bash

source ./venv/bin/activate

echo
echo "Upload package..."
python -m pip install --upgrade twine
python -m twine upload dist/*
echo "...Done!"
