import re

html = open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8').read()
matches = re.findall(r'<button class="btn-tool.*?</button>', html, flags=re.DOTALL)
result = [re.sub(r'<[^>]+>', ' ', m).strip() for m in matches]
with open('c:/Coding/Capcraft/buttons_dump.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))
