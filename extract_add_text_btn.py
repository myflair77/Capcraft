import io
lines = io.open('index.html', 'r', encoding='utf-8').read().split('\n')
for i, line in enumerate(lines):
    if "document.getElementById('btn_add_text_to_shape').addEventListener('click'" in line or "btn_add_text_to_shape" in line:
        io.open('extract_add_text_btn_result.txt', 'w', encoding='utf-8').write('\n'.join(lines[max(0, i-5):min(len(lines), i+80)]))
        break
