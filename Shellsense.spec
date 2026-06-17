# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\shellsense\\ui\\interface.py'],
    pathex=['src'],
    binaries=[],
    datas=[('shellsense_v3.pkl', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tensorflow', 'tensorboard', 'keras', 'torch', 'torchvision', 'torchaudio', 
        'matplotlib', 'pandas', 'mako', 'openpyxl', 'sqlalchemy', 'nltk', 
        'googleapiclient', 'httplib2', 'tzdata', 'cryptography', 'Crypto', 'PIL', 
        'pyarrow', 'cv2', 'psycopg2', 'psycopg2_binary', 'ipython', 'notebook', 
        'tornado', 'jupyter'
    ],
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
    name='Shellsense',
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
