import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
keywords = [
    'object:scaling', 'syncShapeToText', 'uniformScaling',
    'object:modified', 'normalizeScale', 'linkedText',
    'linkedShape', 'originalHeight', 'originalWidth',
    'object:moving', 'object:rotating',
]
for kw in keywords:
    hits = [(i+1, l.strip()[:120]) for i, l in enumerate(lines) if kw in l]
    if hits:
        print(f'\n=== {kw} ===')
        for n, txt in hits:
            print(f'  L{n}: {txt}')
