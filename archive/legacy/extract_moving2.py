import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if "canvas.on('object:moving'" in line:
        start = i
        break
print('\n'.join(lines[start:start+40]))
