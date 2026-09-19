import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "btn_add_text_to_shape" in line:
        start = i
        break
print('\n'.join(lines[start:start+60]))
