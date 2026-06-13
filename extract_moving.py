import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "canvas.on('object:moving'" in line:
        start = i
        break
io.open('moving_full.txt', 'w', encoding='utf-8').write('\n'.join(lines[start:start+50]))
