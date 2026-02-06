@echo off
echo Запуск проекта ЧёПочём...
echo.

echo Проверка Python...
python --version
if %errorlevel% neq 0 (
    echo Ошибка: Python не найден. Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)

echo.
echo Создание виртуального окружения...
if not exist venv (
    python -m venv venv
    echo Виртуальное окружение создано
) else (
    echo Виртуальное окружение уже существует
)

echo.
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo.
echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Применение миграций...
python manage.py makemigrations
python manage.py migrate

echo.
echo Инициализация базовых данных...
python manage.py init_data

echo.
echo Запуск сервера разработки...
echo Откройте браузер и перейдите по адресу: http://127.0.0.1:8000
echo Для остановки сервера нажмите Ctrl+C
echo.
python manage.py runserver

pause



