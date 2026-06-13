import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
for i, line in enumerate(lines):
    if "canvas.on('object:modified'" in line:
        io.open('extract_modified_result.txt', 'w', encoding='utf-8').write('\n'.join(lines[i-5:i+30]))
        break
