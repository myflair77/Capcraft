import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "paletteEl.style.display = 'none'" in line:
        start = i
        break
io.open('color_picker.txt', 'w', encoding='utf-8').write('\n'.join(lines[start-15:start+15]))
