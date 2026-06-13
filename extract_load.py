import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "canvas.loadFromJSON(" in line:
        start = i
        break
io.open('load_json.txt', 'w', encoding='utf-8').write('\n'.join(lines[start:start+100]))
