# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['imzML_Writer.py'],
    pathex=['/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages (2.5.10)','/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages','/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages'],
    binaries=[],
    datas=[('/Users/josephmonaghan/Documents/nanoDESI_raw_to_imzml/Images/Logo-01.png', './Images')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='imzML_Writer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='imzML_Writer',
)
app = BUNDLE(
    coll,
    name='imzML_Writer.app',
    icon=None,
    bundle_identifier=None,
)
