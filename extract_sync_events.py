import io
content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if "canvas.on('object:scaling'" in line:
        start_scaling = i
    if "canvas.on('object:moving'" in line:
        start_moving = i
    if "canvas.on('object:rotating'" in line:
        start_rotating = i

with io.open('sync_events.txt', 'w', encoding='utf-8') as f:
    f.write("=== object:scaling ===\n")
    f.write('\n'.join(lines[start_scaling:start_scaling+50]))
    f.write("\n\n=== object:moving ===\n")
    f.write('\n'.join(lines[start_moving:start_moving+20]))
    f.write("\n\n=== object:rotating ===\n")
    f.write('\n'.join(lines[start_rotating:start_rotating+20]))
