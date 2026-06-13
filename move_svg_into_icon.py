import re

guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    html = f.read()

# We want to find: <span class="button-icon"></span> [optional whitespace/comments] <svg ...</svg>
# and replace it with: <span class="button-icon"><svg ...</svg></span>

# First, capture the exact pattern
pattern = r'<span class="button-icon"></span>\s*(?:<!--.*?-->\s*)?(<svg.*?</svg>)'

def repl(match):
    svg_code = match.group(1)
    return f'<span class="button-icon">{svg_code}</span>'

# Replace!
new_html = re.sub(pattern, repl, html, flags=re.DOTALL)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Moved SVGs inside .button-icon successfully!")
