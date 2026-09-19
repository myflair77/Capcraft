import re
import os

# 1. Fix index.html pin issue
with open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Instead of relying on when createIcons runs at the bottom, run it right before attaching listeners!
target_code = "document.querySelectorAll('.pin-icon').forEach(pin => {"
if 'lucide.createIcons();\n        document.querySelectorAll' not in html:
    html = html.replace(target_code, "lucide.createIcons();\n        " + target_code)

with open('c:/Coding/Capcraft/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update guide.html
if os.path.exists('c:/Coding/Capcraft/guide.html'):
    with open('c:/Coding/Capcraft/guide.html', 'r', encoding='utf-8') as f:
        guide_html = f.read()

    if 'unpkg.com/lucide' not in guide_html:
        guide_html = guide_html.replace('</head>', '    <script src="https://unpkg.com/lucide@latest"></script>\n</head>', 1)

    if 'lucide.createIcons();' not in guide_html:
        guide_html = guide_html.replace('</body>', '    <script>\n        lucide.createIcons();\n    </script>\n</body>', 1)

    if '.icon-small' not in guide_html:
        guide_html = guide_html.replace('</style>', '        .icon-small { width: 16px; height: 16px; display: inline-block; vertical-align: text-bottom; margin-right: 4px; }\n    </style>', 1)

    guide_reps = [
        ('📸 새캡처', '<i data-lucide="camera" class="icon-small"></i> 새캡처'),
        ('↩️', '<i data-lucide="undo-2" class="icon-small"></i>'),
        ('↪️', '<i data-lucide="redo-2" class="icon-small"></i>'),
        ('Abc', '<i data-lucide="type" class="icon-small"></i>'),
        ('😀 이모티콘', '<i data-lucide="smile" class="icon-small"></i> 이모티콘'),
        ('🖼️ 이미지', '<i data-lucide="image" class="icon-small"></i> 이미지'),
        ('💧 모자이크', '<i data-lucide="droplets" class="icon-small"></i> 모자이크'),
        ('✂️ 자르기', '<i data-lucide="crop" class="icon-small"></i> 자르기'),
        ('📋 복사', '<i data-lucide="copy" class="icon-small"></i> 복사'),
        ('📂 열기', '<i data-lucide="folder-open" class="icon-small"></i> 열기'),
        ('💾 저장', '<i data-lucide="save" class="icon-small"></i> 저장'),
        ('🖨️ 인쇄', '<i data-lucide="printer" class="icon-small"></i> 인쇄'),
        ('❌ 닫기', '<i data-lucide="x" class="icon-small"></i> 닫기'),
        ('📌 고정', '<i data-lucide="pin" class="icon-small"></i> 고정'),
        ('🗑️ 개체 모두 지우기', '<i data-lucide="trash-2" class="icon-small"></i> 개체 모두 지우기'),
        ('⚙️ 환경설정', '<i data-lucide="settings" class="icon-small"></i> 환경설정'),
        ('ℹ️ 프로그램 정보 및 가이드', '<i data-lucide="info" class="icon-small"></i> 프로그램 정보 및 가이드'),
        ('📖 프로그램 사용법', '<i data-lucide="book-open" class="icon-small"></i> 프로그램 사용법'),
        ('⌨️ 단축키', '<i data-lucide="keyboard" class="icon-small"></i> 단축키'),
        ('📸', '<i data-lucide="camera" class="icon-small"></i>'),
        ('😀', '<i data-lucide="smile" class="icon-small"></i>'),
        ('🖼️', '<i data-lucide="image" class="icon-small"></i>'),
        ('💧', '<i data-lucide="droplets" class="icon-small"></i>'),
        ('✂️', '<i data-lucide="crop" class="icon-small"></i>'),
        ('📋', '<i data-lucide="copy" class="icon-small"></i>'),
        ('📂', '<i data-lucide="folder-open" class="icon-small"></i>'),
        ('💾', '<i data-lucide="save" class="icon-small"></i>'),
        ('🖨️', '<i data-lucide="printer" class="icon-small"></i>'),
        ('❌', '<i data-lucide="x" class="icon-small"></i>'),
        ('📌', '<i data-lucide="pin" class="icon-small"></i>'),
        ('🗑️', '<i data-lucide="trash-2" class="icon-small"></i>'),
        ('⚙️', '<i data-lucide="settings" class="icon-small"></i>'),
        ('ℹ️', '<i data-lucide="info" class="icon-small"></i>'),
        ('📖', '<i data-lucide="book-open" class="icon-small"></i>'),
        ('⌨️', '<i data-lucide="keyboard" class="icon-small"></i>')
    ]
    for old, new in guide_reps:
        guide_html = guide_html.replace(old, new)
        
    with open('c:/Coding/Capcraft/guide.html', 'w', encoding='utf-8') as f:
        f.write(guide_html)
        
print("Fixed pin and guide icons.")
