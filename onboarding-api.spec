# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('/Users/madhavmishra/Downloads/service-account.json', '.')]
binaries = []
hiddenimports = ['uvicorn', 'uvicorn.loggers', 'uvicorn.loops', 'uvicorn.protocols', 'uvicorn.lifespan.on', 'firebase_admin', 'firebase_admin.firestore', 'google.cloud', 'google.cloud.firestore', 'google.api_core', 'google.api_core.grpc_helpers', 'grpc', 'grpc._cython.cygrpc', 'grpc._auth', 'google.auth', 'google.oauth2', 'cachetools']
tmp_ret = collect_all('app')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='onboarding-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
