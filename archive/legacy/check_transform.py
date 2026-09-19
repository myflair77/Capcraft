import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if "canvas._currentTransform = null;" in line:
        print(f"Found at {i}: {line}")
