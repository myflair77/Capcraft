import re
html = open('c:/Coding/Capcraft/index_backup.html', 'r', encoding='utf-8').read()
matches = re.findall(r'.{0,80}pin-icon.{0,80}', html)
with open('c:/Coding/Capcraft/pin_matches.txt', 'w', encoding='utf-8') as f:
    for m in matches:
        f.write(m + '\n')
