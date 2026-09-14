import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. panel_popout 교체
old_panel = """<div id="panel_popout" class="sub-panel" style="gap:10px;">
            <label style="font-size: 12px; color: var(--text-color); display:flex; align-items:center; gap:5px; cursor:pointer;">
                <input type="checkbox" id="popout_line_toggle" checked> 연결선
            </label>
            <div style="display:flex; align-items:center; gap:5px;" title="연결선 색상/두께">
                <div id="btn_popout_line_color" class="color-btn" style="background-color: #94a3b8; width:16px; height:16px; margin:0; border:1px solid #ccc; cursor:pointer;"></div>
                <input type="number" id="popout_line_weight" min="1" max="10" value="4" style="width: 35px;">
            </div>
            <div style="display:flex; align-items:center; gap:5px;" title="가로 회전">
                <span style="font-size:12px; color:var(--text-color);">가로:</span>
                <input type="number" id="popout_skew_x" min="-45" max="45" value="0" style="width: 40px;">
            </div>
            <div style="display:flex; align-items:center; gap:5px;" title="세로 회전">
                <span style="font-size:12px; color:var(--text-color);">세로:</span>
                <input type="number" id="popout_skew_y" min="-45" max="45" value="0" style="width: 40px;">
            </div>
        </div>"""

new_panel = """<div id="panel_popout" class="sub-panel" style="gap:10px; font-size:12px; align-items:center;">
            <label style="display:flex; align-items:center; gap:3px; cursor:pointer; margin:0;"><input type="checkbox" id="popout_line_toggle" checked> 연결선</label>
            <div id="btn_popout_line_color" class="color-btn" style="background-color: #555555; width:16px; height:16px; margin:0; border:1px solid #ccc; cursor:pointer;" title="선색"></div>
            <input type="number" id="popout_line_weight" min="1" max="20" value="4" style="width: 35px;" title="선 두께">
            
            <span style="margin-left:5px;">가로축:</span><input type="number" id="popout_skew_x" min="-45" max="45" value="0" style="width: 40px;">
            <span>세로축:</span><input type="number" id="popout_skew_y" min="-45" max="45" value="0" style="width: 40px;">
            
            <span style="margin-left:5px;">테두리색:</span><div id="btn_popout_border_color" class="color-btn" style="background-color: #ffffff; width:16px; height:16px; margin:0; border:1px solid #ccc; cursor:pointer;"></div>
            <input type="number" id="popout_border" min="0" max="30" value="10" style="width: 35px;" title="테두리 두께">
            
            <span style="margin-left:5px;">그림자색:</span><div id="btn_popout_shadow_color" class="color-btn" style="background-color: #000000; width:16px; height:16px; margin:0; border:1px solid #ccc; cursor:pointer;"></div>
            <input type="number" id="popout_shadow" min="0" max="100" value="50" style="width: 35px;" title="그림자 강도">
        </div>"""
if old_panel in content:
    content = content.replace(old_panel, new_panel)
else:
    # 혹시 기존 패널이 조금 다를 경우
    content = re.sub(r'<div id="panel_popout" class="sub-panel".*?</div>\s*</div>', new_panel, content, flags=re.DOTALL)


# 2. createPopoutFromObject 의 pad 축소 (외곽선 크기 조절)
content = content.replace("const pad = 40; // padding", "const pad = 10; // padding")

# 3. 환경설정 모달 창 너비 조정 (40px -> 50px)
content = content.replace('id="set_popout_border" value="10" min="0" max="30" style="width:40px;"', 'id="set_popout_border" value="10" min="0" max="30" style="width:50px;"')
content = content.replace('id="set_popout_shadow" value="50" min="0" max="100" style="width:40px;"', 'id="set_popout_shadow" value="50" min="0" max="100" style="width:50px;"')

# 4. updateObjectControls 동기화 로직 교체
old_sync = """document.getElementById('popout_line_toggle').checked = !!obj.showConnectionLine;
                document.getElementById('popout_skew_x').value = obj.tiltX || 0;
                document.getElementById('popout_skew_y').value = obj.tiltY || 0;"""

new_sync = """document.getElementById('popout_line_toggle').checked = obj.showConnectionLine !== false;
                if (document.getElementById('btn_popout_line_color')) document.getElementById('btn_popout_line_color').style.backgroundColor = obj.popoutLineColor || '#555555';
                if (document.getElementById('popout_line_weight')) document.getElementById('popout_line_weight').value = obj.popoutLineWeight || 4;
                document.getElementById('popout_skew_x').value = obj.tiltX || 0;
                document.getElementById('popout_skew_y').value = obj.tiltY || 0;
                if (document.getElementById('btn_popout_border_color')) document.getElementById('btn_popout_border_color').style.backgroundColor = obj.popoutBorderColor || '#ffffff';
                if (document.getElementById('popout_border')) document.getElementById('popout_border').value = obj.popoutBorder !== undefined ? obj.popoutBorder : 10;
                if (document.getElementById('btn_popout_shadow_color')) document.getElementById('btn_popout_shadow_color').style.backgroundColor = obj.popoutShadowColor || '#000000';
                if (document.getElementById('popout_shadow')) document.getElementById('popout_shadow').value = obj.popoutShadow !== undefined ? obj.popoutShadow : 50;"""
content = content.replace(old_sync, new_sync)

# 5. modal_edit 레이아웃 추가
form_html = """<!-- 팝아웃 개체 전용 폼 -->
            <div id="form_edit_popout" style="display:none;">
                <div class="row">
                    <span>크기:</span> <input type="number" id="edit_popout_w" style="width: 60px;"> <span>x</span> <input type="number" id="edit_popout_h" style="width: 60px;">
                    <label style="margin-left:10px; font-size:12px;"><input type="checkbox" id="edit_popout_lock_ratio" checked> 비율 유지</label>
                </div>
                <div class="row">
                    <label style="font-size:12px; margin-right:10px;"><input type="checkbox" id="edit_popout_line_chk"> 연결선 표시</label>
                    <span style="margin-left:5px;">연결선 색상:</span>
                    <div id="edit_popout_line_color" class="color-btn" style="background-color: #555555;"></div>
                    <span style="margin-left:10px;">연결선 두께:</span> <input type="number" id="edit_popout_line_w" min="1" max="20" style="width: 40px;">
                </div>
                <div class="row">
                    <span>가로축 회전:</span> <input type="number" id="edit_popout_skew_x" min="-45" max="45" style="width: 50px;">
                    <span style="margin-left:15px;">세로축 회전:</span> <input type="number" id="edit_popout_skew_y" min="-45" max="45" style="width: 50px;">
                </div>
                <div class="row">
                    <span>테두리 색상:</span>
                    <div id="edit_popout_border_color" class="color-btn" style="background-color: #ffffff;"></div>
                    <span style="margin-left:10px;">테두리 두께:</span> <input type="number" id="edit_popout_border" min="0" max="30" style="width: 40px;">
                    <span style="margin-left:15px;">그림자 색상:</span>
                    <div id="edit_popout_shadow_color" class="color-btn" style="background-color: #000000;"></div>
                    <span style="margin-left:10px;">그림자 강도:</span> <input type="number" id="edit_popout_shadow" min="0" max="100" style="width: 40px;">
                </div>
            </div>

            <!-- 이미지 전용 폼 -->"""
content = content.replace("<!-- 이미지 전용 폼 -->", form_html)


# 6. 더블클릭 이벤트 내 변수 추가 및 form 숨기기
content = content.replace("let origShapeRatio = 1, origImageRatio = 1, origLineRatio = 1;", "let origShapeRatio = 1, origImageRatio = 1, origLineRatio = 1, origPopoutRatio = 1;")
content = content.replace("bindAspectRatio('edit_line_w', 'edit_line_h', 'edit_line_lock_ratio', () => origLineRatio);", "bindAspectRatio('edit_line_w', 'edit_line_h', 'edit_line_lock_ratio', () => origLineRatio);\n        bindAspectRatio('edit_popout_w', 'edit_popout_h', 'edit_popout_lock_ratio', () => origPopoutRatio);")
content = content.replace("document.getElementById('form_edit_image').style.display = 'none';", "document.getElementById('form_edit_image').style.display = 'none';\n            if (document.getElementById('form_edit_popout')) document.getElementById('form_edit_popout').style.display = 'none';")

# 더블클릭 이벤트에서 속성 값 로드
show_edit_block = """            if (isImage) {
                document.getElementById('form_edit_image').style.display = 'block';
                const isGroup = editingObject.type === 'group';
                let ew = Math.round(isGroup ? editingObject.getObjects()[0].width * editingObject.scaleX : editingObject.width * editingObject.scaleX);
                let eh = Math.round(isGroup ? editingObject.getObjects()[0].height * editingObject.scaleY : editingObject.height * editingObject.scaleY);"""

new_show_edit = """            if (editingObject.isPopout) {
                document.getElementById('form_edit_popout').style.display = 'block';
                let ew = Math.round(editingObject.width * editingObject.scaleX);
                let eh = Math.round(editingObject.height * editingObject.scaleY);
                document.getElementById('edit_popout_w').value = ew;
                document.getElementById('edit_popout_h').value = eh;
                origPopoutRatio = (eh === 0) ? 1 : ew / eh;
                
                document.getElementById('edit_popout_line_chk').checked = editingObject.showConnectionLine !== false;
                document.getElementById('edit_popout_line_color').style.backgroundColor = editingObject.popoutLineColor || '#555555';
                document.getElementById('edit_popout_line_w').value = editingObject.popoutLineWeight || 4;
                
                document.getElementById('edit_popout_skew_x').value = editingObject.tiltX || 0;
                document.getElementById('edit_popout_skew_y').value = editingObject.tiltY || 0;
                
                document.getElementById('edit_popout_border_color').style.backgroundColor = editingObject.popoutBorderColor || '#ffffff';
                document.getElementById('edit_popout_border').value = editingObject.popoutBorder !== undefined ? editingObject.popoutBorder : 10;
                
                document.getElementById('edit_popout_shadow_color').style.backgroundColor = editingObject.popoutShadowColor || '#000000';
                document.getElementById('edit_popout_shadow').value = editingObject.popoutShadow !== undefined ? editingObject.popoutShadow : 50;
            } else if (isImage) {"""
content = content.replace(show_edit_block, new_show_edit)


# 7. applyObjectEdit 에서 저장
apply_edit_block = """            if (isImage) {
                const newW = parseInt(document.getElementById('edit_image_w').value);
                const newH = parseInt(document.getElementById('edit_image_h').value);
                let baseW = editingObject.type === 'group' ? editingObject.getObjects()[0].width : editingObject.width;
                let baseH = editingObject.type === 'group' ? editingObject.getObjects()[0].height : editingObject.height;
                editingObject.set({ scaleX: newW / baseW, scaleY: newH / baseH });
                editingObject.setCoords();
            } else if (isText && !isEmoji) {"""

new_apply_edit = """            if (editingObject.isPopout) {
                const newW = parseInt(document.getElementById('edit_popout_w').value);
                const newH = parseInt(document.getElementById('edit_popout_h').value);
                editingObject.set({ 
                    scaleX: newW / editingObject.width, 
                    scaleY: newH / editingObject.height,
                    showConnectionLine: document.getElementById('edit_popout_line_chk').checked,
                    popoutLineColor: document.getElementById('edit_popout_line_color').style.backgroundColor,
                    popoutLineWeight: parseInt(document.getElementById('edit_popout_line_w').value) || 4,
                    tiltX: parseInt(document.getElementById('edit_popout_skew_x').value) || 0,
                    tiltY: parseInt(document.getElementById('edit_popout_skew_y').value) || 0,
                    popoutBorderColor: document.getElementById('edit_popout_border_color').style.backgroundColor,
                    popoutBorder: parseInt(document.getElementById('edit_popout_border').value) || 0,
                    popoutShadowColor: document.getElementById('edit_popout_shadow_color').style.backgroundColor,
                    popoutShadow: parseInt(document.getElementById('edit_popout_shadow').value) || 0
                });
                editingObject.setCoords();
                if (typeof applyPopoutTilt === 'function') applyPopoutTilt(editingObject);
                if (typeof updatePopoutLine === 'function') updatePopoutLine(editingObject);
            } else if (isImage) {"""
content = content.replace(apply_edit_block, new_apply_edit)

# 8. colorpicker 바인딩 추가 (모달 창 내부의 color-btn)
bind_cp_html = """        bindCP('edit_shape_stroke', 'edit_shape_stroke'); bindCP('edit_shape_fill', 'edit_shape_fill');"""
bind_cp_html_new = """        bindCP('edit_shape_stroke', 'edit_shape_stroke'); bindCP('edit_shape_fill', 'edit_shape_fill');
        bindCP('edit_popout_line_color', 'edit_popout_line_c'); bindCP('edit_popout_border_color', 'edit_popout_border_c'); bindCP('edit_popout_shadow_color', 'edit_popout_shadow_c');"""
content = content.replace(bind_cp_html, bind_cp_html_new)


with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("UI patch applied successfully.")
