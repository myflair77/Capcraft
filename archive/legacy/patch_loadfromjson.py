import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure all loadFromJSON calls use window.popoutReviver
content = re.sub(r'canvas\.loadFromJSON\(jsonToLoad, \(\) => \{', r'canvas.loadFromJSON(jsonToLoad, () => {', content)
content = content.replace("canvas.loadFromJSON(jsonToLoad, () => {", "canvas.loadFromJSON(jsonToLoad, () => {") # No-op if same
content = re.sub(r'canvas\.loadFromJSON\(([^,]+),\s*\(\)\s*=>\s*\{', r'canvas.loadFromJSON(\1, () => {', content)

# I will just write a specific replace script
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'canvas.loadFromJSON(' in line and '() => {' in line and 'window.popoutReviver' not in line:
        lines[i] = line.replace('() => {', '() => {').replace('});', '}, window.popoutReviver);')
        # Wait, if `});` is on a different line, this won't work.

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
"
