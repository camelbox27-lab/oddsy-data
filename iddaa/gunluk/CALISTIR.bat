@echo off
chcp 65001 >nul
echo [IDDAA] Excel JSON'a cevriliyor ve GitHub'a pushlaniyor...
echo.
python "%~dp0excel_to_json.py"
