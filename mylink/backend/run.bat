@echo off
REM SmartBot Backend Startup Script for Windows

echo Starting SmartBot Backend...

REM Check if .env exists
if not exist .env (
    echo .env file not found. Copying from .env.example...
    copy .env.example .env
    echo Created .env file. Please update it with your settings.
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run migrations
echo Running database migrations...
alembic upgrade head

REM Start server
echo Starting FastAPI server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

