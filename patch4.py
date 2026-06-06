import codecs
import re

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# Update custom controls hitbox to be massive
content = re.sub(
    r"cornerSize:\s*80,\s*transparentCorners:\s*false",
    r"cornerSize: 100, touchCornerSize: 100, transparentCorners: false",
    content
)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(content)

print("Patch 4 applied: Hit box increased to 100")
