import io
content = io.open('index.html', 'r', encoding='utf-8').read()

def get_block(start_str, num_lines):
    lines = content.split('\n')
    start = -1
    for i, line in enumerate(lines):
        if start_str in line:
            start = i
            break
    if start != -1:
        return '\n'.join(lines[start:start+num_lines])
    return ""

out = []
out.append("--- MOUSE DOWN ---")
out.append(get_block("canvas.on('mouse:down'", 100))
out.append("--- ADD TEXT TO SHAPE ---")
out.append(get_block("document.getElementById('btn_add_text_to_shape').addEventListener", 150))
out.append("--- OBJECT SCALING ---")
out.append(get_block("canvas.on('object:scaling'", 70))

io.open('debug_dump.txt', 'w', encoding='utf-8').write('\n\n'.join(out))
