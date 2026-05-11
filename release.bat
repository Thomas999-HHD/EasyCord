@echo off
set VERSION=6.0.1
echo [1/4] Verifying project (syntax check)...
python -m compileall -q easycord tests || goto :err

echo [2/4] Running bridge safety tests...
pytest tests/test_desktop_bridge.py -v || goto :err

echo [3/4] Creating release archive (EasyCord-v%VERSION%.zip)...
powershell -Command "Compress-Archive -Path easycord, ui, ui/__init__.py, ui/desktop/__init__.py, tests, pyproject.toml, README.md, CHANGELOG.md, AGENTS.md, LICENSE, MANIFEST.in -DestinationPath EasyCord-v%VERSION%.zip -Force" || goto :err

echo [4/4] Syncing with GitHub (origin/main)...
git add .
git commit -m "Release v%VERSION%: Command Center Integration"
git tag -a v%VERSION% -m "Release v%VERSION%"
git push origin main --tags

echo.
echo ─────────────────────────────────────────────────────────────
echo  EasyCord v%VERSION% released successfully!
echo  Archive: EasyCord-v%VERSION%.zip
echo ─────────────────────────────────────────────────────────────
goto :eof

:err
echo.
echo [!] Release failed. Check errors above.
exit /b 1
