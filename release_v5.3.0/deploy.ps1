# EasyCord v5.3.0 Local Release Preparation Script

Write-Host "Preparing EasyCord v5.3.0 local release..." -ForegroundColor Cyan

# 1. Syntax verification
Write-Host "Verifying Python syntax..."
python -m compileall -q easycord tests
if ($LASTEXITCODE -ne 0) {
    Write-Error "Syntax verification failed."
    exit 1
}

# 2. Release-focused tests
Write-Host "Running release-focused tests..."
$env:PYTHONPATH = (Get-Location).Path
pytest tests/test_release_readiness.py tests/test_public_api.py tests/test_developer_toolkit.py -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Release-focused tests failed."
    exit 1
}

# 3. Full test suite
Write-Host "Running full test suite..."
pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Full test suite failed."
    exit 1
}

# 4. Build
Write-Host "Building distribution package..."
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed."
    exit 1
}

# 5. Optional artifact validation
Write-Host "Checking built artifacts when twine is available..."
python -m twine --version *> $null
if ($LASTEXITCODE -eq 0) {
    python -m twine check dist/*
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Twine artifact validation failed."
        exit 1
    }
} else {
    Write-Host "twine is not installed; skipping artifact validation." -ForegroundColor Yellow
}

Write-Host "`nLocal v5.3.0 release preparation complete. Assets are ready in dist/." -ForegroundColor Green
Write-Host "No tag, push, GitHub release, or PyPI upload was performed."
Write-Host "Review release_v5.3.0/notes.md and dist/ before publishing manually."
