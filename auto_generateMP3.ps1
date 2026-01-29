# 1. 自動切換到此腳本所在的資料夾 ($PSScriptRoot 是系統自動抓取的變數)
Set-Location -Path $PSScriptRoot

# 2. 執行 Python 程式
python vocab_audio_md.py
python create_player_mdV6fixed.py


# 3. 暫停畫面，讓你看得到輸出結果 (類似 cmd 的 pause)
Read-Host "執行結束，請按 Enter 鍵關閉視窗..."