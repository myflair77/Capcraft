import re

guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    html = f.read()

pattern = r'(<span class="button-icon"[^>]*>)</span>\s*(?:<!--.*?-->\s*)?(<svg.*?</svg>)'

def repl(match):
    span_open = match.group(1)
    svg_code = match.group(2)
    return f'{span_open}{svg_code}</span>'

new_html = re.sub(pattern, repl, html, flags=re.DOTALL)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Moved remaining SVGs inside .button-icon successfully!")
