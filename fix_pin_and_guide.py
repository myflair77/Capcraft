import re

# FIX INDEX.HTML PIN ICON POSITION
index_file = 'c:/Coding/Capcraft/index.html'
with open(index_file, 'r', encoding='utf-8') as f:
    index_html = f.read()

pin_css_target = ".pin-icon { stroke: #fca5a5; opacity: 0.8; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; }"
pin_css_replacement = ".pin-icon { position: absolute; top: 2px; right: 2px; width: 12px; height: 12px; stroke: #fca5a5; opacity: 0.8; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; fill: none; }"

if pin_css_target in index_html:
    index_html = index_html.replace(pin_css_target, pin_css_replacement)
else:
    # Just in case it's slightly different
    index_html = re.sub(r'\.pin-icon\s*\{([^}]+)\}', r'.pin-icon { position: absolute; top: 2px; right: 2px; width: 12px; height: 12px; fill: none; \1}', index_html)

with open(index_file, 'w', encoding='utf-8') as f:
    f.write(index_html)
print("Fixed index.html pins")


# FIX GUIDE.HTML
guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    guide_html = f.read()

# Make sure lucide creates icons. Let's add an explicit DOMContentLoaded listener just in case it executes too early.
lucide_script = """    <script>
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        });
        // Fallback if DOMContentLoaded already fired
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    </script>"""

guide_html = re.sub(r'<script>\s*lucide\.createIcons\(\);\s*</script>', lucide_script, guide_html)

# Also ensure .icon-small has fill: none
guide_html = guide_html.replace('.icon-small { width: 16px; height: 16px; display: inline-block; vertical-align: text-bottom; margin-right: 4px; }', 
                                '.icon-small { width: 16px; height: 16px; display: inline-block; vertical-align: text-bottom; margin-right: 4px; fill: none; }')

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(guide_html)
print("Fixed guide.html icons")
