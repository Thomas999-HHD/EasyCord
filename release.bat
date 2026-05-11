@echo off
set VERSION=6.0.1
echo [1/4] Verifying project (syntax check)...
python -m compileall -q easycord tests || goto :err

echo [2/4] Running bridge safety tests...
pytest tests/test_desktop_bridge.py -v || goto :err

echo [3/4] Creating release archive (EasyCord-v%VERSION%.zip)...
powershell -Command "Compress-Archive -Path easycord, ui, tests, pyproject.toml, README.md, CHANGELOG.md, AGENTS.md, LICENSE, MANIFEST.in -DestinationPath EasyCord-v%VERSION%.zip -Force" || goto :err

echo [4/4] Syncing with GitHub (origin/main)...
git add .
:: Allow empty commit if everything is already staged/committed
git commit -m "Release v%VERSION%: Command Center Integration" || echo No new changes to commit.

:: Force tag update if it already exists locally
git tag -f -a v%VERSION% -m "Release v%VERSION%"

:: Push main branch first
git push origin main || goto :err

:: Push ONLY the current version tag (force if necessary to sync with remote)
git push origin v%VERSION% -f

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
