with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in [3451, 3689, 4523]: # 0-indexed for 3452, 3690, 4524
    if lines[i].strip() == '});':
        lines[i] = lines[i].replace('});', '}, window.popoutReviver);')
    else:
        # fallback if indentation changed
        lines[i] = lines[i].replace('});', '}, window.popoutReviver);')

with open('index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patched loadFromJSON calls!")
