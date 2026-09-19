import re
import sys

with open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add Lucide script to head
if 'unpkg.com/lucide' not in html:
    html = html.replace('</head>', '    <script src="https://unpkg.com/lucide@latest"></script>\n</head>')

# 2. Add lucide.createIcons() to bottom of body
if 'lucide.createIcons();' not in html:
    html = html.replace('</body>', '    <script>\n        lucide.createIcons();\n    </script>\n</body>')

# 3. Add global CSS for icons to match sizes
css_addition = """
        /* Lucide Vector Icons UI CSS */
        .btn-tool i[data-lucide] { width: 22px; height: 22px; pointer-events: none; }
        .icon-small { width: 16px; height: 16px; display: inline-block; vertical-align: text-bottom; margin-right: 4px; }
        .pin-icon { width: 12px; height: 12px; }
        .btn-align i[data-lucide] { width: 14px; height: 14px; pointer-events: none; }
        .modal-close i[data-lucide] { width: 16px; height: 16px; pointer-events: none; }
"""
if '/* Lucide Vector Icons UI CSS */' not in html:
    html = html.replace('</style>', f'{css_addition}\n</style>')

# Replace main tool buttons
replacements = [
    (r'<button class="btn-tool" id="btn_new_capture"><span class="icon">📸</span>새캡처</button>',
     '<button class="btn-tool" id="btn_new_capture"><span class="icon"><i data-lucide="camera"></i></span>새캡처</button>'),
    (r'<button class="btn-tool disabled" id="btn_undo"><span class="icon">↩️</span>뒤로</button>',
     '<button class="btn-tool disabled" id="btn_undo"><span class="icon"><i data-lucide="undo-2"></i></span>뒤로</button>'),
    (r'<button class="btn-tool disabled" id="btn_redo"><span class="icon">↪️</span>앞으로</button>',
     '<button class="btn-tool disabled" id="btn_redo"><span class="icon"><i data-lucide="redo-2"></i></span>앞으로</button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_text"><span class="icon">Abc</span>텍스트<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_text"><span class="icon"><i data-lucide="type"></i></span>텍스트<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_pen"><span class="icon"><svg.*?</svg></span>펜<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_pen"><span class="icon"><i data-lucide="pen-tool"></i></span>펜<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_shape"><span class="icon"><svg.*?</svg></span>도형<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_shape"><span class="icon"><i data-lucide="shapes"></i></span>도형<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_emoji"><span class="icon">😀</span>이모티콘<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_emoji"><span class="icon"><i data-lucide="smile"></i></span>이모티콘<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_image"><span class="icon">🖼️</span>이미지<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_image"><span class="icon"><i data-lucide="image"></i></span>이미지<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_mosaic"><span class="icon">💧</span>모자이크<span class="pin-icon" title="고정하기">📌</span></button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_mosaic"><span class="icon"><i data-lucide="droplets"></i></span>모자이크<i data-lucide="pin" class="pin-icon" title="고정하기"></i></button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_eraser">\s*<span class="icon"><img.*?></span>지우개\s*</button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_eraser"><span class="icon"><i data-lucide="eraser"></i></span>지우개</button>'),
    (r'<button class="btn-tool group-edit disabled" id="btn_tool_crop"><span class="icon">✂️</span>자르기</button>',
     '<button class="btn-tool group-edit disabled" id="btn_tool_crop"><span class="icon"><i data-lucide="crop"></i></span>자르기</button>'),
    (r'<button class="btn-tool disabled" id="btn_action_copy"><span class="icon">📋</span>복사</button>',
     '<button class="btn-tool disabled" id="btn_action_copy"><span class="icon"><i data-lucide="copy"></i></span>복사</button>'),
    (r'<button class="btn-tool" id="btn_action_open" title="JSON파일을 열어서 작업을 계속할 수 있습니다."><span class="icon">📂</span>열기</button>',
     '<button class="btn-tool" id="btn_action_open" title="JSON파일을 열어서 작업을 계속할 수 있습니다."><span class="icon"><i data-lucide="folder-open"></i></span>열기</button>'),
    (r'<button class="btn-tool disabled" id="btn_action_save"><span class="icon">💾</span>저장</button>',
     '<button class="btn-tool disabled" id="btn_action_save"><span class="icon"><i data-lucide="save"></i></span>저장</button>'),
    (r'<button class="btn-tool disabled" id="btn_action_print"><span class="icon">🖨️</span>인쇄</button>',
     '<button class="btn-tool disabled" id="btn_action_print"><span class="icon"><i data-lucide="printer"></i></span>인쇄</button>'),
    (r'<button class="btn-tool red" id="btn_action_close"><span class="icon">❌</span>닫기</button>',
     '<button class="btn-tool red" id="btn_action_close"><span class="icon"><i data-lucide="x"></i></span>닫기</button>'),

    # Align Buttons
    (r'<button class="btn-align([^>]*) data-val="left"([^>]*)><svg.*?</svg></button>',
     '<button class="btn-align\\1 data-val="left"\\2><i data-lucide="align-left"></i></button>'),
    (r'<button class="btn-align([^>]*) data-val="center"([^>]*)><svg.*?</svg></button>',
     '<button class="btn-align\\1 data-val="center"\\2><i data-lucide="align-center"></i></button>'),
    (r'<button class="btn-align([^>]*) data-val="right"([^>]*)><svg.*?</svg></button>',
     '<button class="btn-align\\1 data-val="right"\\2><i data-lucide="align-right"></i></button>'),

    # Utility & Sub-panel
    (r'<button id="btn_clear_all" (.*?)>🗑️ 개체 모두 지우기</button>',
     '<button id="btn_clear_all" \\1><i data-lucide="trash-2" class="icon-small"></i> 개체 모두 지우기</button>'),

    # Modal Headers
    (r'<span>🖼️ 이미지 영역 선택</span>', '<span><i data-lucide="image" class="icon-small"></i> 이미지 영역 선택</span>'),
    (r'<span>⚙️ 환경설정</span>', '<span><i data-lucide="settings" class="icon-small"></i> 환경설정</span>'),
    (r'<span>ℹ️ 프로그램 정보 및 가이드</span>', '<span><i data-lucide="info" class="icon-small"></i> 프로그램 정보 및 가이드</span>'),
    (r'<span>⌨️ 단축키</span>', '<span><i data-lucide="keyboard" class="icon-small"></i> 단축키</span>'),
    (r'<button class="modal-close"([^>]*)>❌</button>',
     '<button class="modal-close"\\1><i data-lucide="x"></i></button>'),
]

for pat, rep in replacements:
    html = re.sub(pat, rep, html, flags=re.DOTALL)

with open('c:/Coding/Capcraft/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Icons replaced in index.html successfully.")
