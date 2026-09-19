import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    js_code_to_insert = """
            } else if (targetColorBtn === 'set_pen_bg' || targetColorBtn === 'btn_pen_bg') {
                const elId = targetColorBtn === 'set_pen_bg' ? 'set_pen_bg_color' : 'btn_pen_bg';
                document.getElementById(elId).style.backgroundColor = c.h;
                if(targetColorBtn === 'set_pen_bg') document.getElementById('btn_pen_bg').style.backgroundColor = c.h;
                else document.getElementById('set_pen_bg_color').style.backgroundColor = c.h;
                sysPenBgColor = c.h;
"""

    for i, line in enumerate(lines):
        if "} else if (targetColorBtn === 'pen' || targetColorBtn === 'set_pen_ballpoint' || targetColorBtn === 'set_pen_highlighter') {" in line:
            lines.insert(i, js_code_to_insert)
            break

    with open('index.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("JS patched color picker")

patch_file()
