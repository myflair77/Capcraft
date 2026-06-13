import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if "let sysPenBallpointWeight = 3;" in line:
            lines.insert(i+2, "        let sysPenBgColor = 'transparent';\n        let sysPenBgOpacity = 0;\n")
            break

    for i, line in enumerate(lines):
        if "'set_pen_highlighter_opacity'," in line:
            lines[i] = line.replace("'set_pen_highlighter_opacity',", "'set_pen_highlighter_opacity', 'set_pen_bg_opacity',")
            break

    # Fix the pen_type change listener
    for i, line in enumerate(lines):
        if "document.getElementById('pen_type').addEventListener('change', (e) => {" in line:
            # We want to find the if/else block inside it.
            for j in range(i, i+20):
                if "if (val === 'ballpoint') {" in lines[j]:
                    lines.insert(j+4, "                document.getElementById('label_pen_highlighter_intensity').style.display = 'none';\n                document.getElementById('pen_highlighter_intensity_input').style.display = 'none';\n")
                if "} else {" in lines[j]:
                    lines.insert(j+5, "                document.getElementById('label_pen_highlighter_intensity').style.display = 'inline';\n                document.getElementById('pen_highlighter_intensity_input').style.display = 'inline';\n")
            break

    with open('index.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("JS patched")

patch_file()
