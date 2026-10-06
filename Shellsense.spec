# -*- mode: python ; coding: utf-8 -*-
import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('shellsense_v3.pkl', '.'),
        ('src/shellsense/web/static', 'src/shellsense/web/static')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'tensorboard', 'cv2', 'transformers', 'onnxruntime', 'matplotlib', 'IPython', 'scipy', 'nltk', 'keras', 'h5py'],
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
    name='ShellSense',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
