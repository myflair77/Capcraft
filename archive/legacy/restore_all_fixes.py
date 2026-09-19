import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add pin icons to tool buttons
buttons_to_pin = [
    'btn_tool_shape',
    'btn_tool_emoji',
    'btn_tool_image',
    'btn_tool_mosaic',
    'btn_tool_eraser',
    'btn_tool_pen'
]

for btn_id in buttons_to_pin:
    # Find the button end tag or just insert before </button>
    pattern = rf'(<button[^>]*id="{btn_id}"[^>]*>.*?(?=</button>))(</button>)'
    # Check if not already pinned
    if 'class="pin-icon"' not in content and btn_id in content:
        content = re.sub(pattern, r'\1<span class="pin-icon" title="고정하기">📌</span>\2', content, flags=re.DOTALL)

# 2. Add pin CSS
pin_css = """
        .pin-icon { position: absolute; bottom: 2px; right: 2px; font-size: 10px; cursor: pointer; opacity: 0.3; transition: all 0.2s; pointer-events: auto; }
        .pin-icon.active { opacity: 1; transform: scale(1.2); text-shadow: 0 0 2px rgba(0,0,0,0.5); }
"""
if '.pin-icon' not in content:
    content = content.replace('</style>', pin_css + '</style>')

# 3. Fix text background color bug (TypeError properties of null)
# We change text color fetching logic in addText mouseDownHandler to use global variables
# Actually, I injected it earlier via btn_action_copy listener. Let's fix that block.
# Wait, let's just replace the injected logic completely.
old_logic = """
            const txtColor = document.getElementById('setting_text_color').value;
            const txtBgColor = document.getElementById('setting_text_bg_color').value;
            const txtSize = parseInt(document.getElementById('setting_text_size').value) || 20;
"""
new_logic = """
            const txtColor = window.textColor || '#000000';
            const txtBgColor = typeof getTextBgOpacity === 'function' ? getTextBgOpacity() : '';
            const txtSize = parseInt(document.getElementById('text_size_input') ? document.getElementById('text_size_input').value : 50) || 50;
"""
content = content.replace(old_logic, new_logic)

# 4. Implement deactivateActiveTool
deactivate_func = """
        function deactivateActiveTool() {
            const activeBtn = document.querySelector('.btn-tool.group-edit.active');
            if (activeBtn) {
                const pin = activeBtn.querySelector('.pin-icon');
                if (pin && pin.classList.contains('active')) return;
                activeBtn.click(); // This toggles it off
            }
        }
"""
if 'function deactivateActiveTool' not in content:
    content = content.replace('function updateGlobalCursor() {', deactivate_func + '\n        function updateGlobalCursor() {')

# 5. Inject pin click logic
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
if "document.querySelectorAll('.pin-icon')" not in content:
    content = content.replace("document.querySelectorAll('.btn-tool').forEach(btn => {", pin_js + "\n        document.querySelectorAll('.btn-tool').forEach(btn => {")

# 6. Inject deactivateActiveTool calls where tools finish
# For shapes: line 3960, 4041, 4450, 4574, 4593
deact_targets = [
    "saveHistory();\n            }\n        });\n\n        canvas.on('mouse:down'",
    "currentShape = null; arrowHead = null; clickPoints = [];\n            updateObjectSelectability();\n            canvas.requestRenderAll(); saveHistory();",
    "canvas.requestRenderAll(); saveHistory();\n                return;\n            }",
    "canvas.requestRenderAll(); saveHistory(); \n            } \n\n            //",
    "currentShape = null; arrowHead = null;\n                updateObjectSelectability();\n                canvas.requestRenderAll(); saveHistory();\n"
]

for t in deact_targets:
    replacement = t.replace("saveHistory();", "saveHistory(); deactivateActiveTool();")
    content = content.replace(t, replacement)

# Replace another saveHistory(); for liveEmojiImgObj if it doesn't match
t2 = "liveEmojiImgObj = null;\n                            updateObjectSelectability();\n                            canvas.requestRenderAll();\n                            saveHistory();"
content = content.replace(t2, t2.replace("saveHistory();", "saveHistory(); deactivateActiveTool();"))

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Pin feature and text box fix injected.")
