# 強制設定控制台編碼為 UTF-8
chcp 65001 >$null
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8


# 1. 取得腳本所在目錄 (不切換目錄，只存變數)
$ScriptDir = $PSScriptRoot

# 2. 執行 Python 程式 (使用完整路徑指向腳本)
# Python 會在當前所在的目錄 (例如：字典整理01) 尋找 mp3.md
Read-Host "將開始執行 (按 Enter 繼續)..."

python "$ScriptDir\vocab_audio_md.py"
python "$ScriptDir\create_player_mdV6fixed.py"

# 3. 暫停畫面
Read-Host "執行結束，請按 Enter 鍵關閉視窗..."
