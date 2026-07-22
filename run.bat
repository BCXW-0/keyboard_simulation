@echo off
cd /d "%~dp0"
pyw -3 keyboard_relay_gui.pyw
if errorlevel 1 (
  py -3 keyboard_relay.py
)
