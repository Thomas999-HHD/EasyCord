# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the EasyCord desktop shell."""
from pathlib import Path

ROOT = Path(SPECPATH).parent  # one level up from desktop/

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT / 'desktop')],
    binaries=[],
    datas=[
        (str(ROOT / 'EasyCord.html'),        'web'),
        (str(ROOT / 'easycord-ui'),          'web/easycord-ui'),
    ],
    hiddenimports=['webview.platforms.winforms', 'webview.platforms.edgechromium'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EasyCord',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                       # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'desktop' / 'icon.ico') if (ROOT / 'desktop' / 'icon.ico').exists() else None,
)
