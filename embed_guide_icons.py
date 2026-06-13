import re
import urllib.request

guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    html = f.read()

# Find all <i data-lucide="..."> tags
matches = re.findall(r'<i data-lucide="([^"]+)" class="([^"]+)"></i>', html)

# Fetch and replace each icon
cache = {}
for icon_name, class_name in set(matches):
    if icon_name not in cache:
        url = f'https://unpkg.com/lucide-static@latest/icons/{icon_name}.svg'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                svg = response.read().decode('utf-8')
                
                # Add the classes to the SVG
                svg = svg.replace('<svg', f'<svg class="lucide lucide-{icon_name} {class_name}"')
                cache[icon_name] = svg
        except Exception as e:
            print(f"Failed to fetch {icon_name}: {e}")
            continue

for icon_name, svg in cache.items():
    # Replace all instances of the <i> tag with the <svg> tag
    html = re.sub(rf'<i data-lucide="{icon_name}" class="icon-small"></i>', svg, html)

# Remove the script tags since we don't need them anymore
html = re.sub(r'<script src="https://unpkg\.com/lucide[^>]*></script>', '', html)
html = re.sub(r'<script>\s*lucide\.createIcons\(\);\s*</script>', '', html)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(html)
print("All icons embedded successfully!")
