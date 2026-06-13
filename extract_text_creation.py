import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "document.getElementById('btn_add_text_to_shape').addEventListener('click', function" in line:
        start = i
        break
io.open('add_text_func.txt', 'w', encoding='utf-8').write('\n'.join(lines[start:start+150]))
