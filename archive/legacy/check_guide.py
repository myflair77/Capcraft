import re

# Dump guide.html tools section
html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()
matches = re.findall(r'<li>.*?</li>', html, flags=re.DOTALL)
with open('c:/Coding/Capcraft/guide_dump.txt', 'w', encoding='utf-8') as f:
    for m in matches:
        if 'strong' in m:
            f.write(m.replace('\n', ' ') + '\n')
