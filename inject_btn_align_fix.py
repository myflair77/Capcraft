import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the align button event listeners if any, or append them
    # Currently, in Capcraft, the align buttons might be handled generically or not at all for live updates.
    # We will inject a global listener for .btn-align
    
    align_listener = """
        document.querySelectorAll('.btn-align').forEach(btn => {
            btn.addEventListener('mousedown', e => e.preventDefault());
            btn.addEventListener('click', function() {
                const group = this.closest('.btn-group');
                if (group) {
                    group.querySelectorAll('.btn-align').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    const val = this.getAttribute('data-align');
                    
                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        updateActiveText();
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            updateActiveText();
                        }
                    }
                }
            });
        });
"""
    if "document.querySelectorAll('.btn-align').forEach(btn => {" not in content:
        content = content.replace("document.querySelector('emoji-picker').addEventListener", align_listener + "\n        document.querySelector('emoji-picker').addEventListener")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
