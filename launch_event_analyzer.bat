@echo off
chcp 65001 >nul
title Writer Tool - 事件分析工具
cd /d "%~dp0"
python analyze_events.py --gui
if errorlevel 1 pause
