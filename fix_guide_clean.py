import re

guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Clean up old duplicated <i data-lucide...> tags
html = re.sub(r'<i data-lucide="[^"]+"\s*class="icon-small"></i>\s*', '', html)

# 2. Inject fresh <i data-lucide...> tags
reps = {
    '새캡처 기능 그룹': '<i data-lucide="camera" class="icon-small"></i> 새캡처 기능 그룹',
    '텍스트 도구 (Text)': '<i data-lucide="type" class="icon-small"></i> 텍스트 도구 (Text)',
    '펜 도구 (Pen)': '<i data-lucide="pen-tool" class="icon-small"></i> 펜 도구 (Pen)',
    '도형 도구 (Shapes)': '<i data-lucide="shapes" class="icon-small"></i> 도형 도구 (Shapes)',
    '이미지 삽입 (Insert Image)': '<i data-lucide="image" class="icon-small"></i> 이미지 삽입 (Insert Image)',
    '모자이크 도구 (Mosaic)': '<i data-lucide="droplets" class="icon-small"></i> 모자이크 도구 (Mosaic)',
    '자르기 도구 (Crop Canvas)': '<i data-lucide="crop" class="icon-small"></i> 자르기 도구 (Crop Canvas)',
    '저장 옵션 (Save Options)': '<i data-lucide="save" class="icon-small"></i> 저장 옵션 (Save Options)',
    '프로젝트 열기 &amp; 클립보드 복사': '<i data-lucide="folder-open" class="icon-small"></i> 프로젝트 열기 &amp; 클립보드 복사',
    '프로젝트 열기 & 클립보드 복사': '<i data-lucide="folder-open" class="icon-small"></i> 프로젝트 열기 & 클립보드 복사',
    '조작 팁 &amp; 핵심 노하우': '<i data-lucide="lightbulb" class="icon-small"></i> 조작 팁 &amp; 핵심 노하우',
    '조작 팁 & 핵심 노하우': '<i data-lucide="lightbulb" class="icon-small"></i> 조작 팁 & 핵심 노하우'
}

for k, v in reps.items():
    html = html.replace(k, v)

# 3. Fix the script tag to use onload
html = re.sub(r'<script src="https://unpkg\.com/lucide@latest"></script>', '', html)
html = re.sub(r'<script>\s*document\.addEventListener[^<]+</script>', '', html, flags=re.DOTALL)
html = re.sub(r'<script>\s*if \(typeof lucide[^<]+</script>', '', html, flags=re.DOTALL)
html = re.sub(r'<script>\s*lucide\.createIcons\(\);\s*</script>', '', html, flags=re.DOTALL)

# Insert the script right before </body>
onload_script = """    <script src="https://unpkg.com/lucide@latest" onload="lucide.createIcons()"></script>
</body>"""
if '</body>' in html:
    html = html.replace('</body>', onload_script)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(html)
print("Guide.html cleaned and fixed!")
