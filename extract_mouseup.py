import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
for i, line in enumerate(lines):
    if "canvas.on('mouse:up'" in line:
        print('\n'.join(lines[i:i+60]))
        break
