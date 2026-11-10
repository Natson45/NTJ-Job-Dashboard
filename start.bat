@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
if not exist .venv\Scripts\streamlit.exe (
  echo Installing packages, this takes a minute or two...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Package install failed. Scroll up for the error.
    pause
    exit /b 1
  )
)
python -c "import authlib" 2>nul || (
  echo Installing new packages...
  python -m pip install -r requirements.txt
)
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Created .env - paste your connection string into it, save, then run start.bat again.
  notepad .env
  pause
  exit /b
)
start "" http://localhost:8501
streamlit run app.py
if errorlevel 1 pause
