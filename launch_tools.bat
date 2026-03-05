@echo off
chcp 65001 >nul
title Writer Tool - 工具箱
cd /d "%~dp0"
python start_tools.py
if errorlevel 1 pause
