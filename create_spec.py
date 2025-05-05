#!/usr/bin/env python
"""
Create PyInstaller Spec File for VISTA3D
"""

spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['vista3d_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('vista3d', 'vista3d'),
        ('config.yaml', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'torch',
        'monai',
        'nibabel',
        'yaml',
        'numpy',
        'vista3d.scripts.infer',
        'vista3d.modeling',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='vista3d',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='vista3d',
)
"""

# Write the spec file
with open('vista3d.spec', 'w') as f:
    f.write(spec_content)

print("Successfully created vista3d.spec file")
