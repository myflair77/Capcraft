import re

html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()
match = re.search(r'<div class="button-header">.*?텍스트 도구 \(Text\)', html, re.DOTALL)
if match:
    with open('c:/Coding/Capcraft/debug_html.txt', 'w', encoding='utf-8') as f:
        f.write(match.group(0))
    print("Written to debug_html.txt")
else:
    print("Not found")
