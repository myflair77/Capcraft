# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
from pathlib import Path
import sys
sys.path.insert(0, SPECPATH)
from scripts.prepare_release_resources import prepare
resources = prepare(Path(SPECPATH))
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
    pathex=[str(resources)],
    binaries=ocr_bins + ort_bins + collect_dynamic_libs('uiautomation'),
    datas=[('index.html', '.'), (str(resources / 'icon.ico'), '.'), (str(resources / 'licenses'), 'licenses'), ('LICENSE', '.'), ('SOURCE_CODE.md', '.'), ('vendor', 'vendor'), ('popout-quality.js', '.'), ('presentation-refresh.js', '.'), ('ocr-ui.js', '.'), ('models/ocr', 'models/ocr')] + ocr_data + ort_data,
    hiddenimports=['_guide_resource'] + ocr_imports + ort_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['scripts/frozen_diagnostics.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Qt uses Windows' ICU API. A build-tool PATH (e.g. Poppler) can make
# PyInstaller collect a different icuuc.dll with suffixed, incompatible exports.
# Never redistribute that DLL under the Windows system DLL name.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icuin.dll', 'icu.dll'}]
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
    icon=[str(resources / 'icon.ico')],
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
