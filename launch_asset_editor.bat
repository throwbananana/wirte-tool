@echo off
chcp 65001 >nul
title Writer Tool - 资源管理器
cd /d "%~dp0"
python start_asset_editor.py
if errorlevel 1 pause
