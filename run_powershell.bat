@echo off
:: 不切換目錄，保留當前執行環境的目錄 (CWD)

:: 使用絕對路徑執行主目錄下的 PowerShell 腳本 (Bypass 執行策略限制)
powershell -ExecutionPolicy Bypass -File "%~dp0auto_generateMP3.ps1"

:: 暫停畫面，確保視窗不會執行完瞬間關閉 (方便查看結果或錯誤訊息)
pause