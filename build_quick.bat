@echo off
chcp 65001 >nul
echo ====================================
echo   BUILD EXE CHO DỰ ÁN VMIX MONITOR
echo ====================================
echo.

REM Kiểm tra Python đã cài chưa
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt!
    echo Vui lòng cài Python từ: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python đã được cài đặt
echo.

REM Chạy script build
python build_exe.py

echo.
echo ====================================
echo   HOÀN TẤT
echo ====================================
echo.
echo File EXE đã được tạo trong thư mục "dist"
echo.
pause
