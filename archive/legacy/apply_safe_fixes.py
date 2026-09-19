import os

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Hit detection
content = content.replace("cornerSize: 10,", "cornerSize: 10,\n                touchCornerSize: 24,")
content = content.replace("padding: 5,", "padding: 10,")
content = content.replace("targetFindTolerance: 10,", "targetFindTolerance: 15,")

# 2. SVG save button
svg_btn = '<button data-format="svg">SVG 저장</button>\n                    '
if 'data-format="svg"' not in content:
    content = content.replace('<button data-format="pdf">PDF 저장</button>', svg_btn + '<button data-format="pdf">PDF 저장</button>')

# 3. Rotation cursor
old_rot_svg = "const rotateIconSvg = \"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='11' fill='white' stroke='%233b82f6' stroke-width='2'/><path d='M15.5 12c0 1.93-1.57 3.5-3.5 3.5s-3.5-1.57-3.5-3.5 1.57-3.5 3.5-3.5v2l3.5-3-3.5-3v2c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5h-1.5z' fill='%233b82f6'/></svg>\";"
new_rot_svg = "const rotateIconSvg = \"data:image/svg+xml;utf8,\" + encodeURIComponent(\"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='18' height='18'><circle cx='12' cy='12' r='11' fill='white' stroke='#3b82f6' stroke-width='2'/><path d='M15.5 12c0 1.93-1.57 3.5-3.5 3.5s-3.5-1.57-3.5-3.5 1.57-3.5 3.5-3.5v2l3.5-3-3.5-3v2c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5h-1.5z' fill='#3b82f6'/></svg>\");"
content = content.replace(old_rot_svg, new_rot_svg)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Safe fixes applied.")
