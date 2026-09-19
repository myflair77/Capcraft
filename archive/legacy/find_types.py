import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
keywords = [
    'isMediaImage', 'isEmoji', "type === 'image'",
    'lockScalingY', 'lockScalingX',
    'lockMovementX', 'lockMovementY',
]
for kw in keywords:
    hits = [(i+1, l.strip()[:140]) for i, l in enumerate(lines) if kw in l]
    if hits:
        print(f'\n=== {kw} ===')
        for n, txt in hits[:15]:
            print(f'  L{n}: {txt}')
