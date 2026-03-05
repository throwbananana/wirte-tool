@echo off
chcp 65001 >nul
title Writer Tool - 助手配置编辑器
cd /d "%~dp0"
python start_assistant_event_editor.py
if errorlevel 1 pause
