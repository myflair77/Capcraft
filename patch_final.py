import re

# 1. FIX PIN IN INDEX.HTML
index_html = open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8').read()

old_listener = """        document.querySelectorAll('.pin-icon').forEach(pin => {
            pin.addEventListener('click', function(e) {
                e.stopPropagation();
                this.classList.toggle('active');
            });
        });"""

new_listener = """        document.addEventListener('click', function(e) {
            const pin = e.target.closest('.pin-icon');
            if (pin) {
                e.stopPropagation();
                pin.classList.toggle('active');
            }
        }, true);"""

if old_listener in index_html:
    index_html = index_html.replace(old_listener, new_listener)
    open('c:/Coding/Capcraft/index.html', 'w', encoding='utf-8').write(index_html)
    print("Fixed index.html")

# 2. FIX GUIDE.HTML ICONS
guide_html = open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8').read()

# Replace inline SVGs
guide_html = re.sub(r'<svg[^>]*>\s*<path d="M3 12c3-8 9-8 12 0s9 8 9 0"\s*/>\s*</svg>', '<i data-lucide="pen-tool" class="icon-small"></i>', guide_html)
guide_html = re.sub(r'<svg[^>]*>\s*<rect x="3" y="3" width="18" height="18"\s*/>\s*</svg>', '<i data-lucide="shapes" class="icon-small"></i>', guide_html)

# Add Lucide icons to headers if not already added
reps = {
    '텍스트 도구 (Text)': '<i data-lucide="type" class="icon-small"></i> 텍스트 도구 (Text)',
    '펜 도구 (Pen)': '<i data-lucide="pen-tool" class="icon-small"></i> 펜 도구 (Pen)',
    '도형 도구 (Shapes)': '<i data-lucide="shapes" class="icon-small"></i> 도형 도구 (Shapes)',
    '이미지 삽입 (Insert Image)': '<i data-lucide="image" class="icon-small"></i> 이미지 삽입 (Insert Image)',
    '모자이크 도구 (Mosaic)': '<i data-lucide="droplets" class="icon-small"></i> 모자이크 도구 (Mosaic)',
    '자르기 도구 (Crop Canvas)': '<i data-lucide="crop" class="icon-small"></i> 자르기 도구 (Crop Canvas)',
    '새캡처 기능 그룹': '<i data-lucide="camera" class="icon-small"></i> 새캡처 기능 그룹',
    '저장 옵션 (Save Options)': '<i data-lucide="save" class="icon-small"></i> 저장 옵션 (Save Options)',
    '프로젝트 열기 &amp; 클립보드 복사': '<i data-lucide="folder-open" class="icon-small"></i> 프로젝트 열기 &amp; 클립보드 복사',
    '프로젝트 열기 & 클립보드 복사': '<i data-lucide="folder-open" class="icon-small"></i> 프로젝트 열기 & 클립보드 복사',
    '조작 팁 &amp; 핵심 노하우': '<i data-lucide="lightbulb" class="icon-small"></i> 조작 팁 &amp; 핵심 노하우',
    '조작 팁 & 핵심 노하우': '<i data-lucide="lightbulb" class="icon-small"></i> 조작 팁 & 핵심 노하우'
}

for k, v in reps.items():
    if v not in guide_html:
        guide_html = guide_html.replace(k, v)

# Ensure lucide.createIcons() runs after body
if 'lucide.createIcons();' not in guide_html:
    guide_html = guide_html.replace('</body>', '    <script>\n        lucide.createIcons();\n    </script>\n</body>')

open('c:/Coding/Capcraft/guide.html', 'w', encoding='utf-8').write(guide_html)
print("Fixed guide.html")
