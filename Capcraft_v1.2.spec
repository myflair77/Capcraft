# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
ocr_data, ocr_bins, ocr_imports = collect_all('rapidocr')
ocr_data += [('natural-pens.js', '.')]
ocr_data += [('line-anchors.js', '.')]
ocr_data += [('shape-pens.js', '.')]
ocr_data += [('stroke-effects.js', '.')]
ocr_data += [('smart-guides.js', '.')]
ort_data, ort_bins, ort_imports = collect_all('onnxruntime')
for package in ('kiwipiepy', 'kiwipiepy_model', 'lingua'):
    data, binaries, imports = collect_all(package)
    ocr_data += data
    ocr_bins += binaries
    ocr_imports += imports

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ocr_bins + ort_bins,
    datas=[('index.html', '.'), ('guide.html', '.'), ('icon.ico', '.'), ('vendor', 'vendor'), ('popout-quality.js', '.'), ('presentation-refresh.js', '.'), ('ocr-ui.js', '.'), ('models/ocr', 'models/ocr')] + ocr_data + ort_data,
    hiddenimports=ocr_imports + ort_imports,
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
    [],
    exclude_binaries=True,
    name='Capcraft v1.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Capcraft v1.2',
)
