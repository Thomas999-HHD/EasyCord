# EasyCord v5.2.0 Deployment Script

Write-Host "🚀 Preparing EasyCord v5.2.0 Release..." -ForegroundColor Cyan

# 1. Verification
Write-Host "🔍 Verifying code..."
python -m compileall -q easycord tests
if ($LASTEXITCODE -ne 0) { 
    Write-Error "Verification failed! Please check for syntax errors."
    exit 1 
}

# 2. Build
Write-Host "📦 Building distribution package..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
python -m build
if ($LASTEXITCODE -ne 0) { 
    Write-Error "Build failed!"
    exit 1 
}

# 3. Release Commands (Instructional)
Write-Host "`n✅ Build complete! Assets ready in dist/`n" -ForegroundColor Green
Write-Host "To finish the release, run:"
Write-Host "---------------------------"
Write-Host "1. Git Tag:      git tag -a v5.2.0 -m 'Release v5.2.0'"
Write-Host "2. Git Push:     git push origin master --tags"
Write-Host "3. PyPI Upload:  twine upload dist/*"
Write-Host "4. GH Release:   gh release create v5.2.0 --title 'EasyCord v5.2.0' --notes-file release_v5.2.0/notes.md dist/*"
Write-Host "---------------------------"
