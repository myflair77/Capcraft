import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
for i, line in enumerate(lines):
    if 'isDrawing = false;' in line:
        io.open('extract_mouseup_result.txt', 'w', encoding='utf-8').write('\n'.join(lines[i-20:i+40]))
        break
