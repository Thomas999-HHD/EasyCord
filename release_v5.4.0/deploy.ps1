# EasyCord v5.4.0 Local Release Preparation Script

Write-Host "Preparing EasyCord v5.4.0 local release..." -ForegroundColor Cyan

Write-Host "Verifying Python syntax..."
python -m compileall -q easycord tests
if ($LASTEXITCODE -ne 0) {
    Write-Error "Syntax verification failed."
    exit 1
}

Write-Host "Running full test suite..."
$env:PYTHONPATH = (Get-Location).Path
pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "Full test suite failed."
    exit 1
}

Write-Host "Building distribution package..."
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed."
    exit 1
}

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

Write-Host "`nLocal v5.4.0 release preparation complete. Assets are ready in dist/." -ForegroundColor Green
Write-Host "No tag, push, GitHub release, or PyPI upload was performed by this script."
Write-Host "Review release_v5.4.0/notes.md and dist/ before publishing manually."
