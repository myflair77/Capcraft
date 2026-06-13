import sys

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

patched = False
for i, line in enumerate(lines):
    if "const isText = (editingObject.type === 'i-text' || editingObject.type === 'text');" in line:
        if 'const isEmoji' in lines[i+1]:
            lines.insert(i+2, '            if (isText && !isEmoji) return;\n')
            patched = True
            break

if patched:
    with open('index.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Patched double click handler.')
else:
    print('Target not found.')
