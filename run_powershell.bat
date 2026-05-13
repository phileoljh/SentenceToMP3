@echo off
title "TTS Audio Generator"
set "ScriptDir=%~dp0"

echo [TTS] Starting...

python "%ScriptDir%vocab_audio_md.py"
python "%ScriptDir%create_player_mdV6fixed.py"

echo.
echo [TTS] Done!
pause