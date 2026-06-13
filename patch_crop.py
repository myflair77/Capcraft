import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Add syncFabricContainerSize(); to performEdgeCrop
pattern = re.compile(r'(panX = 0; panY = 0;\s*)(applyFitZoom\(\); applyCanvasClipping\(\);)')
if pattern.search(content):
    content = pattern.sub(r'\1syncFabricContainerSize();\n                        \2', content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched performEdgeCrop")
else:
    print("Could not find pattern in performEdgeCrop")
