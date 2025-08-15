@echo off
title Install Backend

echo Installing Backend Packages...
echo.

if exist .venv (
    call .venv\Scripts\activate
    goto install
)

if exist venv (
    call venv\Scripts\activate
    goto install
)

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

:install
python -m pip install --upgrade pip
pip install uvicorn[standard]
pip install fastapi
pip install python-dotenv
pip install pydantic
pip install sqlalchemy
pip install numpy
pip install pandas
pip install redis
pip install httpx

echo.
echo Testing...
python -c "import uvicorn; print('uvicorn OK')"
python -c "import fastapi; print('fastapi OK')"

echo.
echo Done!
echo.
pause