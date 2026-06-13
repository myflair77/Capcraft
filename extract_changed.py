import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "textObj.on('changed'" in line:
        start = i
        break
io.open('changed_event.txt', 'w', encoding='utf-8').write('\n'.join(lines[start:start+40]))
