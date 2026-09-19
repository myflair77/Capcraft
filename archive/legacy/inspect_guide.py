import re

html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()
matches = re.findall(r'<div class="button-header">.*?</div>', html, re.DOTALL)
if matches:
    print(matches[0][:500])
else:
    print("No button-header found")
