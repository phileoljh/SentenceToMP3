@echo off
title TTS Audio Master V7 (Decoupled)
set "ScriptDir=%~dp0"
set PYTHONIOENCODING=utf-8

echo [TTS Master] Starting generation process...
echo.

rem 1. Run Edge TTS Audio Generator
python "%ScriptDir%vocab_audio_md.py"

rem 2. Generate V6 Monolithic Player (For comparison)
python "%ScriptDir%create_player_mdV6fixed.py"

rem 3. Generate V7 Decoupled Player (Separated UI and data)
python "%ScriptDir%create_player_v7_decoupled.py"

echo.
echo [TTS Master] Done! Both player_v6_fixed.html and player_v7_decoupled.html generated.
echo Please open index2.html to compare!
echo.


