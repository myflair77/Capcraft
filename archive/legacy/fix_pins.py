import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Clean up duplicate CSS
content = content.replace(".pin-icon { position: absolute; bottom: 2px; right: 2px; font-size: 10px; cursor: pointer; opacity: 0.3; transition: all 0.2s; pointer-events: auto; }\n        .pin-icon.active { opacity: 1; transform: scale(1.2); text-shadow: 0 0 2px rgba(0,0,0,0.5); }\n", "")

pin_css = """
        .pin-icon { position: absolute; bottom: 2px; right: 2px; font-size: 10px; cursor: pointer; opacity: 0.3; transition: all 0.2s; pointer-events: auto; }
        .pin-icon.active { opacity: 1; transform: scale(1.2); text-shadow: 0 0 2px rgba(0,0,0,0.5); }
"""
# Insert CSS ONLY at the first </style>
content = content.replace('</style>', pin_css + '</style>', 1)

# 2. Add pin icons to all buttons
buttons_to_pin = [
    'btn_tool_shape',
    'btn_tool_emoji',
    'btn_tool_image',
    'btn_tool_mosaic',
    'btn_tool_eraser',
    'btn_tool_pen'
]

for btn_id in buttons_to_pin:
    # Check if this specific button already has the pin
    # We can just remove it if it exists and add it again to be safe
    # Wait, the easiest way is to use regex.
    # Check if the button block has a pin-icon
    btn_pattern = re.compile(rf'(<button[^>]*id="{btn_id}"[^>]*>.*?)</button>', re.DOTALL)
    match = btn_pattern.search(content)
    if match:
        btn_html = match.group(1)
        if 'class="pin-icon"' not in btn_html:
            content = btn_pattern.sub(rf'\g<1><span class="pin-icon" title="고정하기">📌</span></button>', content)

# 3. Check if pin click logic is missing
# Actually, the previous script injected it once, so it should be there. Let's make sure it's not missing.
if "pin.addEventListener('click'" not in content:
    pin_js = """
        document.querySelectorAll('.pin-icon').forEach(pin => {
            pin.addEventListener('click', (e) => {
                e.stopPropagation();
                pin.classList.toggle('active');
                const btn = pin.closest('.btn-tool');
                if (!btn.classList.contains('active')) {
                    btn.click();
                }
            });
        });
"""
    content = content.replace("document.querySelectorAll('.btn-tool').forEach(btn => {", pin_js + "\n        document.querySelectorAll('.btn-tool').forEach(btn => {")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Pin icons fixed.")
