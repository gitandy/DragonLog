@echo off
set PATH=venv\Lib\site-packages\qt6_applications\Qt\bin

call venv\Scripts\activate.bat

start designer %1
