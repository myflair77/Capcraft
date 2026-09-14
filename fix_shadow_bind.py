import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("bindPopoutInput('popout_shadow', 'popoutShadow', parseFloat, applyPopoutTilt);", "bindPopoutInput('popout_shadow', 'popoutShadow', parseFloat, regeneratePopoutBase);")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed popoutShadow binding!")
