import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. mouse:down 이벤트에서 팝아웃 선택 시 panel_popout 강제 표시 로직 추가
mouse_down_target = """            // === 텍스트 편집 모드 보호 및 드래그 선택 강화 ===
            if (!activeTool && o.target) {
                let editingText = null;"""
mouse_down_patch = """            // === 텍스트 편집 모드 보호 및 드래그 선택 강화 ===
            if (!activeTool && o.target) {
                if (o.target.isPopout) {
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    const panel = document.getElementById('panel_popout');
                    if (panel) panel.classList.add('active');
                }
                let editingText = null;"""
content = content.replace(mouse_down_target, mouse_down_patch)

# 2. panel_popout에 있는 버튼들의 bindCP 연결
bindcp_target = """        bindCP('set_popout_line_color', 'set_popout_line'); bindCP('set_popout_border_color', 'set_popout_border_c'); bindCP('set_popout_shadow_color', 'set_popout_shadow_c');"""
bindcp_patch = """        bindCP('set_popout_line_color', 'set_popout_line'); bindCP('set_popout_border_color', 'set_popout_border_c'); bindCP('set_popout_shadow_color', 'set_popout_shadow_c');
        bindCP('btn_popout_line_color', 'popout_line_c'); bindCP('btn_popout_border_color', 'popout_border_c'); bindCP('btn_popout_shadow_color', 'popout_shadow_c');"""
if "bindCP('btn_popout_line_color', 'popout_line_c');" not in content:
    content = content.replace(bindcp_target, bindcp_patch)

# 3. color_palette 클릭 시 팝아웃 속성 연동 로직 추가
color_patch_target = """                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                }"""
color_patch_code = """                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                } else if (['popout_line_c', 'popout_border_c', 'popout_shadow_c', 'edit_popout_line_c', 'edit_popout_border_c', 'edit_popout_shadow_c'].includes(targetColorBtn)) {
                    // Update the button color visually
                    const btnId = targetColorBtn.startsWith('edit_') ? targetColorBtn.replace('_c', 'olor') : 'btn_' + targetColorBtn.replace('_c', '_color');
                    const btnEl = document.getElementById(btnId);
                    if (btnEl) btnEl.style.backgroundColor = c.h;
                    
                    // If target is btn_ (not edit modal), immediately apply to active object
                    if (!targetColorBtn.startsWith('edit_')) {
                        const activeObj = canvas.getActiveObject();
                        if (activeObj && activeObj.isPopout) {
                            if (targetColorBtn === 'popout_line_c') activeObj.set('popoutLineColor', c.h);
                            else if (targetColorBtn === 'popout_border_c') activeObj.set('popoutBorderColor', c.h);
                            else if (targetColorBtn === 'popout_shadow_c') activeObj.set('popoutShadowColor', c.h);
                            
                            if (typeof regeneratePopoutBase === 'function') regeneratePopoutBase(activeObj);
                            if (typeof updatePopoutLine === 'function') updatePopoutLine(activeObj);
                            canvas.requestRenderAll();
                            saveHistory();
                        }
                    }
                }"""
if "popout_line_c" not in content[content.find(color_patch_target):]:
    content = content.replace(color_patch_target, color_patch_code)

# panel_popout 이벤트 리스너 추가 (숫자 변경 시 실시간 반영)
# 만약 기존에 bindPopoutInput 이 있다면, 거기에 새 속성들도 추가해야 함.
bind_popout_input_target = """        function bindPopoutInput(id, key, isFloat) {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', function() {
                const activeObj = canvas.getActiveObject();
                if (activeObj && activeObj.isPopout) {
                    let val = isFloat ? parseFloat(this.value) : parseInt(this.value);
                    activeObj.set(key, val);
                    if (key === 'tiltX' || key === 'tiltY' || key === 'angle') {
                        if (typeof applyPopoutTilt === 'function') applyPopoutTilt(activeObj);
                    } else if (key === 'popoutBorder' || key === 'popoutShadow' || key === 'popoutLineWeight') {
                        if (typeof regeneratePopoutBase === 'function') regeneratePopoutBase(activeObj);
                        if (typeof updatePopoutLine === 'function') updatePopoutLine(activeObj);
                    }
                    canvas.requestRenderAll();
                    saveHistory();
                }
            });
        }"""
bind_popout_calls_target = """        bindPopoutInput('popout_skew_x', 'tiltX', false);
        bindPopoutInput('popout_skew_y', 'tiltY', false);"""
bind_popout_calls_patch = """        bindPopoutInput('popout_skew_x', 'tiltX', false);
        bindPopoutInput('popout_skew_y', 'tiltY', false);
        bindPopoutInput('popout_border', 'popoutBorder', false);
        bindPopoutInput('popout_shadow', 'popoutShadow', false);
        bindPopoutInput('popout_line_weight', 'popoutLineWeight', false);"""
if "bindPopoutInput('popout_border'" not in content:
    content = content.replace(bind_popout_calls_target, bind_popout_calls_patch)

# popout_line_toggle 체크박스 이벤트 추가
popout_toggle_target = """        bindPopoutInput('popout_skew_y', 'tiltY', false);"""
popout_toggle_patch = """        bindPopoutInput('popout_skew_y', 'tiltY', false);
        const popToggle = document.getElementById('popout_line_toggle');
        if (popToggle) {
            popToggle.addEventListener('change', function() {
                const activeObj = canvas.getActiveObject();
                if (activeObj && activeObj.isPopout) {
                    activeObj.set('showConnectionLine', this.checked);
                    if (typeof updatePopoutLine === 'function') updatePopoutLine(activeObj);
                    canvas.requestRenderAll();
                    saveHistory();
                }
            });
        }"""
if "popout_line_toggle" not in content[content.find(popout_toggle_target):content.find(popout_toggle_target)+500]:
    content = content.replace(popout_toggle_target, popout_toggle_patch)

# 4. createPopoutFromObject 의 pad 축소 (0으로 수정하여 여백 아예 없애기)
content = content.replace("const pad = 10; // padding to allow dynamic border and shadow", "const pad = 0; // padding removed to perfectly fit bounds")
content = content.replace("const pad = 40; // padding", "const pad = 0; // padding removed")

# regeneratePopoutBase 여백 보정. 
# pad가 0이 되면 외부 테두리(borderW)를 그릴 때 객체의 폭을 벗어날 수 있음. 
# 하지만 사용자는 외곽선이 팝아웃 크기에 딱 맞기를 원하므로, 테두리가 약간 벗어나더라도 bounding box 안에 들어오도록 크롭 크기를 조정하지 않는다.
# 대신 object의 left/top을 cw/2 가 아니라 딱맞게 수정한다.
# 사실 cw/2, ch/2 는 crop 캔버스 내부에서의 원본 그림 위치이므로 center에 그리는 것이 맞다.

# 5. modal_edit (더블클릭 개체 수정 창) 분기 처리 수정
# 어제 실패했던 `if (isImage) { \n document.getElementById('form_edit_image').style.display = 'block';` 부분을 정규식으로 교체한다.
show_edit_re = re.compile(r'(\s*)if \(isImage\) \{\s*document\.getElementById\(\'form_edit_image\'\)\.style\.display = \'block\';\s*let imgW, imgH;\s*if \(editingObject\.type === \'group\'\) {')

new_show_edit = r"""\1if (editingObject.isPopout) {
\1    document.getElementById('form_edit_popout').style.display = 'block';
\1    let ew = Math.round(editingObject.width * editingObject.scaleX);
\1    let eh = Math.round(editingObject.height * editingObject.scaleY);
\1    document.getElementById('edit_popout_w').value = ew;
\1    document.getElementById('edit_popout_h').value = eh;
\1    origPopoutRatio = (eh === 0) ? 1 : ew / eh;
\1    
\1    document.getElementById('edit_popout_line_chk').checked = editingObject.showConnectionLine !== false;
\1    document.getElementById('edit_popout_line_color').style.backgroundColor = editingObject.popoutLineColor || '#555555';
\1    document.getElementById('edit_popout_line_w').value = editingObject.popoutLineWeight || 4;
\1    
\1    document.getElementById('edit_popout_skew_x').value = editingObject.tiltX || 0;
\1    document.getElementById('edit_popout_skew_y').value = editingObject.tiltY || 0;
\1    
\1    document.getElementById('edit_popout_border_color').style.backgroundColor = editingObject.popoutBorderColor || '#ffffff';
\1    document.getElementById('edit_popout_border').value = editingObject.popoutBorder !== undefined ? editingObject.popoutBorder : 10;
\1    
\1    document.getElementById('edit_popout_shadow_color').style.backgroundColor = editingObject.popoutShadowColor || '#000000';
\1    document.getElementById('edit_popout_shadow').value = editingObject.popoutShadow !== undefined ? editingObject.popoutShadow : 50;
\1} else if (isImage) {
\1    document.getElementById('form_edit_image').style.display = 'block';
\1    let imgW, imgH;
\1    if (editingObject.type === 'group') {"""

content = show_edit_re.sub(new_show_edit, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Final comprehensive popout patch applied.")
