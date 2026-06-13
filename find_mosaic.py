import io

lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if 'mosaic' in l.lower() or '모자이크' in l:
        print(f'{i+1}: {l.strip()[:100]}'.encode('utf-8', 'ignore').decode('utf-8'))
