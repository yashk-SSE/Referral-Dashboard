@echo off
REM Double-click this file to preview the dashboard locally.
REM Serves this folder over http://localhost so the dashboard loads YOUR local
REM data/index files instead of falling back to the live GitHub Pages site.
REM Opens index.preview.html if it exists (work-in-progress copy), else index.html.

cd /d "%~dp0"

if exist index.preview.html (
    set TARGET=index.preview.html
) else (
    set TARGET=index.html
)

echo Starting local server on http://localhost:8743 ...
echo Serving: %TARGET%
echo.

start "SolarSquare Local Server (close this window to stop)" cmd /k python -m http.server 8743
timeout /t 2 /nobreak >nul
start "" http://localhost:8743/%TARGET%

echo Done. A server window has opened separately — close it when you're finished previewing.
