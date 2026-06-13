import re

guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    html = f.read()

# Fix double class attributes in SVG tags
# Find all <svg ...> opening tags
def fix_svg_tag(match):
    tag = match.group(0)
    # Extract all classes from all class="..." attributes
    classes = []
    for cls_match in re.finditer(r'class="([^"]+)"', tag):
        classes.extend(cls_match.group(1).split())
    
    # Remove duplicates but preserve order roughly
    unique_classes = list(dict.fromkeys(classes))
    
    # Remove all class="..." attributes from the tag
    tag_no_class = re.sub(r'\s*class="[^"]+"', '', tag)
    
    # Insert the merged class string
    return tag_no_class.replace('<svg', f'<svg class="{" ".join(unique_classes)}"')

html = re.sub(r'<svg[^>]+>', fix_svg_tag, html)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(html)
print("Fixed double class attributes in guide.html")
