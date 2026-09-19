import re

html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()
match = re.search(r'<i data-lucide="type".*?도구 \(Text\)', html)
print(match.group(0) if match else "Not found")
