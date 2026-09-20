"""Static import/export check for packaged Qt and its adjacent VC runtime."""
from pathlib import Path
import sys
import pefile

root = (Path(sys.argv[1]) if len(sys.argv) > 1 else
        Path(__file__).resolve().parents[1] / 'dist-dev' / 'Capcraft v1.2') / '_internal'
qt = root / 'PyQt6' / 'Qt6' / 'bin'
directories = [root, qt, Path('C:/Windows/System32')]
failures = 0
for target in [root/'PyQt6'/'QtWidgets.pyd', qt/'Qt6Widgets.dll', qt/'Qt6Gui.dll', qt/'Qt6Core.dll']:
    pe = pefile.PE(str(target))
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        name = entry.dll.decode()
        if name.lower().startswith(('api-ms-', 'ext-ms-')): continue
        dependency = next((d/name for d in directories if (d/name).is_file()), None)
        if dependency is None:
            print(target.name, 'MISSING DLL', name); failures += 1; continue
        dep = pefile.PE(str(dependency), max_symbol_exports=100000)
        exports = {s.name for s in getattr(dep, 'DIRECTORY_ENTRY_EXPORT', type('Empty',(),{'symbols':[]})()).symbols}
        for symbol in entry.imports:
            if symbol.name and symbol.name not in exports:
                print(target.name, 'MISSING SYMBOL', name, symbol.name.decode(), 'FROM', dependency)
                failures += 1
if failures:
    raise SystemExit(1)
print('PASS packaged Qt imports resolve to compatible DLL exports')
