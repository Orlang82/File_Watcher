@echo off
chcp 65001 >nul
echo 🚀 Компиляция File Watcher в exe файл...
echo.

REM Проверяем наличие PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ❌ PyInstaller не установлен. Устанавливаем...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ Не удалось установить PyInstaller
        pause
        exit /b 1
    )
)

REM Удаляем старые файлы сборки
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo 📦 Начинаем компиляцию...
echo.

REM Компилируем с включением всех модулей
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name="FileWatcher" ^
    --icon="icon.ico" ^
    --hidden-import=config ^
    --hidden-import=config.settings ^
    --hidden-import=config.watch_rules ^
    --hidden-import=core ^
    --hidden-import=core.utils ^
    --hidden-import=core.file_handler ^
    --hidden-import=core.watcher ^
    --hidden-import=ui ^
    --hidden-import=ui.notifications ^
    --hidden-import=ui.tray_app ^
    --add-data="config;config" ^
    --add-data="core;core" ^
    --add-data="ui;ui" ^
    --distpath="dist" ^
    --workpath="build" ^
    main.py

if errorlevel 1 (
    echo.
    echo ❌ Ошибка компиляции!
    pause
    exit /b 1
)

echo.
echo ✅ Компиляция завершена успешно!
echo 📁 Exe файл находится в папке: dist\FileWatcher.exe
echo.

REM Показываем размер файла в байтах и мегабайтах
for %%I in ("dist\FileWatcher.exe") do (
    set /a size_mb=%%~zI / 1048576
    echo 📊 Размер файла: %%~zI байт (примерно !size_mb! МБ)
)

echo.
echo 🎯 Готово! Скопируйте FileWatcher.exe на локальную машину для запуска.
pause