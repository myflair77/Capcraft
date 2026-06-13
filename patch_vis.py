import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    sync_visibility = '''
        if (document.getElementById('pen_type') && document.getElementById('label_pen_highlighter_intensity')) {
            if (document.getElementById('pen_type').value === 'ballpoint') {
                document.getElementById('label_pen_highlighter_intensity').style.display = 'none';
                document.getElementById('pen_highlighter_intensity_input').style.display = 'none';
            } else {
                document.getElementById('label_pen_highlighter_intensity').style.display = 'inline';
                document.getElementById('pen_highlighter_intensity_input').style.display = 'inline';
            }
        }
'''
    if "function updatePenBrush() {" in content:
        content = content.replace("function updatePenBrush() {", "function updatePenBrush() {\n" + sync_visibility)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Visibility patched")

patch_file()
