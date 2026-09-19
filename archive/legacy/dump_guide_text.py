import re
html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()
text = re.sub(r'<[^>]+>', ' ', html)
with open('c:/Coding/Capcraft/guide_text.txt', 'w', encoding='utf-8') as f:
    f.write(text)
