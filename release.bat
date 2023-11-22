@echo off

call venv\Scripts\activate.bat

python -m pip install --upgrade twine
python -m twine upload dist/*
pause
