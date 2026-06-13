import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if "textObj.on('changed'" in line:
        print(f"Line {i}: {line}")
