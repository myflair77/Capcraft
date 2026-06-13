import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add listeners for text size inputs
    size_listeners = """
        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', updateActiveText);
            sizeInput.addEventListener('change', updateActiveText);
        }
        const editSizeInput = document.getElementById('edit_text_size');
        if (editSizeInput) {
            editSizeInput.addEventListener('input', function() {
                if(document.getElementById('text_size_input')) {
                    document.getElementById('text_size_input').value = this.value;
                }
                updateActiveText();
            });
        }
"""
    if "document.getElementById('text_size_input').addEventListener('input'" not in content:
        content = content.replace("document.querySelector('emoji-picker').addEventListener", size_listeners + "\n        document.querySelector('emoji-picker').addEventListener")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
