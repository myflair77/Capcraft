import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    js_code_to_insert = """
            // Add event listeners for new pen/shape opacity sync
            ['pen_bg_opacity_input', 'shape_bg_opacity_input', 'pen_highlighter_intensity_input'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', (e) => {
                        const val = e.target.value;
                        if (id === 'pen_bg_opacity_input') {
                            if (document.getElementById('set_pen_bg_opacity')) document.getElementById('set_pen_bg_opacity').value = val;
                            sysPenBgOpacity = parseInt(val) / 100;
                        } else if (id === 'shape_bg_opacity_input') {
                            if (document.getElementById('set_shape_opacity_val')) document.getElementById('set_shape_opacity_val').value = val;
                            sysShapeOpacity = parseInt(val) / 100;
                        } else if (id === 'pen_highlighter_intensity_input') {
                            if (document.getElementById('set_pen_highlighter_opacity')) document.getElementById('set_pen_highlighter_opacity').value = val;
                        }
                    });
                }
            });

            ['set_pen_bg_opacity', 'set_shape_opacity_val', 'set_pen_highlighter_opacity'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', (e) => {
                        const val = e.target.value;
                        if (id === 'set_pen_bg_opacity') {
                            if (document.getElementById('pen_bg_opacity_input')) document.getElementById('pen_bg_opacity_input').value = val;
                            sysPenBgOpacity = parseInt(val) / 100;
                        } else if (id === 'set_shape_opacity_val') {
                            if (document.getElementById('shape_bg_opacity_input')) document.getElementById('shape_bg_opacity_input').value = val;
                            sysShapeOpacity = parseInt(val) / 100;
                        } else if (id === 'set_pen_highlighter_opacity') {
                            if (document.getElementById('pen_highlighter_intensity_input')) document.getElementById('pen_highlighter_intensity_input').value = val;
                        }
                    });
                }
            });
"""

    # We will just append it into the DOMContentLoaded block or near the text_bg_opacity_input event listeners
    for i, line in enumerate(lines):
        if "text_bg_opacity_input" in line and "addEventListener" in line:
            lines.insert(i, js_code_to_insert)
            break

    # We also need to add 'btn_pen_bg' to bindCP calls
    for i, line in enumerate(lines):
        if "bindCP('btn_pen_color', 'pen');" in line:
            lines.insert(i+1, "            bindCP('btn_pen_bg', 'set_pen_bg');\n")
            break

    with open('index.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("JS patched")

patch_file()
