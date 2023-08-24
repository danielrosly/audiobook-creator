@echo off

python -m venv .\venv
call .\venv\Scripts\activate.bat
call .\venv\Scripts\python.exe -m pip install -r requirements.txt