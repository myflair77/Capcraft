import io
content = io.open('index_fef5f0a.html', 'r', encoding='utf-16').read()
lines = content.split('\n')
start = 0
for i, line in enumerate(lines):
    if "canvas.on('object:scaling'" in line:
        start = i
        break
io.open('orig_scaling_full.txt', 'w', encoding='utf-8').write('\n'.join(lines[start:start+100]))
