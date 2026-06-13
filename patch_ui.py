import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 1. panel_pen UI modification
    old_pen_ui = '''<span style="margin-left:8px;">선굵기:</span><input type="number" id="pen_weight" value="3" min="1" style="width: 40px; padding: 4px;">
<span>선색상:</span><div id="btn_pen_color" class="color-btn" style="background-color: #E03C31;"></div>'''
    new_pen_ui = '''<span style="margin-left:8px;">선 굵기:</span><input type="number" id="pen_weight" value="3" min="1" style="width: 40px; padding: 4px;">
<span>선 색상:</span><div id="btn_pen_color" class="color-btn" style="background-color: #E03C31;"></div>
<span style="margin-left:8px;">배경 색상:</span><div id="btn_pen_bg" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
<span style="margin-left:8px;">배경 투명도:</span><input type="number" id="pen_bg_opacity_input" value="0" min="0" max="100" style="width: 40px; padding: 4px;">
<span id="label_pen_highlighter_intensity" style="margin-left:8px; display:none;">형광펜 농도:</span><input type="number" id="pen_highlighter_intensity_input" value="30" min="0" max="100" style="width: 40px; padding: 4px; display:none;">'''
    content = content.replace(old_pen_ui, new_pen_ui)

    # 2. panel_shape UI modification
    old_shape_ui = '''<span id="label_fill_color">배경:</span><div id="btn_fill_color" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>'''
    new_shape_ui = '''<span id="label_fill_color">배경 색상:</span><div id="btn_fill_color" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
<span style="margin-left:8px;">배경 투명도:</span><input type="number" id="shape_bg_opacity_input" value="20" min="0" max="100" style="width: 40px; padding: 4px;">'''
    content = content.replace(old_shape_ui, new_shape_ui)
    
    # 3. modal_settings pen settings
    old_pen_settings = '''<div style="font-weight: bold; margin-bottom: 5px; color: var(--accent-blue);">펜 설정</div>
<div class="setting-group" style="margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; font-size: 12px;">
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
<span>볼펜 선 굵기:</span> <input type="number" id="set_pen_ballpoint_weight" value="3" min="1" max="50" style="width:50px;">
<span>볼펜 색상:</span> <div id="set_pen_ballpoint_color" class="color-btn" style="background-color: #E03C31;"></div>
</div>
<div style="display: flex; align-items: center; gap: 10px;">
<span>형광펜 선 굵기:</span> <input type="number" id="set_pen_highlighter_weight" value="20" min="1" max="100" style="width:50px;">
<span>형광펜 색상:</span> <div id="set_pen_highlighter_color" class="color-btn" style="background-color: rgba(255, 255, 0, 0.3);"></div>
<span style="margin-left:3px;">형광펜 색상 농도:</span> <input type="number" id="set_pen_highlighter_opacity" value="30" min="0" max="100" style="width:45px;">
</div>
</div>'''
    new_pen_settings = '''<div style="font-weight: bold; margin-bottom: 5px; color: var(--accent-blue);">펜 설정</div>
<div class="setting-group" style="margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; font-size: 12px;">
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
<span>볼펜 선 굵기:</span> <input type="number" id="set_pen_ballpoint_weight" value="3" min="1" max="50" style="width:50px;">
<span>볼펜 색상:</span> <div id="set_pen_ballpoint_color" class="color-btn" style="background-color: #E03C31;"></div>
</div>
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
<span>형광펜 선 굵기:</span> <input type="number" id="set_pen_highlighter_weight" value="20" min="1" max="100" style="width:50px;">
<span>형광펜 색상:</span> <div id="set_pen_highlighter_color" class="color-btn" style="background-color: rgba(255, 255, 0, 0.3);"></div>
<span style="margin-left:3px;">형광펜 색상 농도:</span> <input type="number" id="set_pen_highlighter_opacity" value="30" min="0" max="100" style="width:45px;">
</div>
<div style="display: flex; align-items: center; gap: 10px;">
<span>배경 색상:</span> <div id="set_pen_bg_color" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
<span>배경 투명도:</span> <input type="number" id="set_pen_bg_opacity" value="0" min="0" max="100" style="width:50px;">
</div>
</div>'''
    content = content.replace(old_pen_settings, new_pen_settings)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
patch_file()
