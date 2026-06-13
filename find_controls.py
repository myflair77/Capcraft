import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
keywords = [
    'controls.mt', 'controls.mb', 'controls.ml', 'controls.mr',
    'controls.tl', 'controls.tr', 'controls.bl', 'controls.br',
    'setControlVisible', 'cornerStyle', 'cornerColor',
    'lockScalingX', 'lockScalingY', 'lockScaling',
    'fabric.Object.prototype',
    'controlsAboveOverlay',
]
for kw in keywords:
    hits = [(i+1, l.strip()[:140]) for i, l in enumerate(lines) if kw in l]
    if hits:
        print(f'\n=== {kw} ===')
        for n, txt in hits:
            print(f'  L{n}: {txt}')
