
@echo off
:: 切換到此 .bat 檔案所在的目錄 (由系統自動判定，無需手寫路徑)
cd /d "%~dp0"

:: 執行 Python 程式
powershell
::python mypython.py

:: 暫停畫面，確保視窗不會執行完瞬間關閉 (方便查看結果或錯誤訊息)
pause