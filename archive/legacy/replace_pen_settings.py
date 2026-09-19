import sys

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''                <div style="display: flex; align-items: center; gap: 10px;">
                    <span>형광펜 선 굵기:</span> <input type="number" id="set_pen_highlighter_weight" value="20" min="1" max="100" style="width:50px;">
                    <span>형광펜 색상:</span> <div id="set_pen_highlighter_color" class="color-btn" style="background-color: rgba(255, 255, 0, 0.3);"></div>
                    <span style="margin-left:3px;">형광펜 색상 농도:</span> <input type="number" id="set_pen_highlighter_opacity" value="30" min="0" max="100" style="width:45px;">
                </div>'''

new_content = '''                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <span>형광펜 선 굵기:</span> <input type="number" id="set_pen_highlighter_weight" value="20" min="1" max="100" style="width:50px;">
                    <span>형광펜 색상:</span> <div id="set_pen_highlighter_color" class="color-btn" style="background-color: rgba(255, 255, 0, 0.3);"></div>
                    <span style="margin-left:3px;">형광펜 색상 농도:</span> <input type="number" id="set_pen_highlighter_opacity" value="30" min="0" max="100" style="width:45px;">
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span>배경 색상:</span> <div id="set_pen_bg_color" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
                    <span>배경 투명도:</span> <input type="number" id="set_pen_bg_opacity" value="0" min="0" max="100" style="width:50px;">
                </div>'''

if target in content:
    content = content.replace(target, new_content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully replaced pen settings.')
else:
    print('Target not found in file.')
