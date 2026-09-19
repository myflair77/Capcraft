import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Sync align buttons
    old_align = """                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        updateActiveText();
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            updateActiveText();
                        }
                    }"""

    new_align = """                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        if (document.getElementById('text_align')) document.getElementById('text_align').value = val;
                        updateActiveText();
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            if (document.getElementById('edit_text_align')) document.getElementById('edit_text_align').value = val;
                            updateActiveText();
                        }
                    }"""

    if old_align in content:
        content = content.replace(old_align, new_align)
    else:
        print("old_align not found")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched align sync")

if __name__ == '__main__':
    main()
