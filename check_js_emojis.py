import re

with open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script.*?>(.*?)</script>', html, re.DOTALL)
js_content = "\n".join(scripts)

emojis = ['📸', '↩️', '↪️', '😀', '🖼️', '💧', '✂️', '📋', '📂', '💾', '🖨️', '❌', '📌', '🗑️', '⚙️', 'ℹ️', 'Abc']
found_in_js = {e: js_content.count(e) for e in emojis}

with open('c:/Coding/Capcraft/js_emojis.txt', 'w', encoding='utf-8') as out:
    for e, count in found_in_js.items():
        if count > 0:
            out.write(f"Emoji {e} found {count} times\n")
