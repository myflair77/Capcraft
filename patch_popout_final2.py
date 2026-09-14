import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. mouse:down 이벤트에서 sub_toolbar.style.display = 'block' 누락 수정
mouse_down_target = """                if (o.target.isPopout) {
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    const panel = document.getElementById('panel_popout');
                    if (panel) panel.classList.add('active');
                }"""
mouse_down_patch = """                if (o.target.isPopout) {
                    document.getElementById('sub_toolbar').style.display = 'block';
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    const panel = document.getElementById('panel_popout');
                    if (panel) panel.classList.add('active');
                }"""
content = content.replace(mouse_down_target, mouse_down_patch)

# selection:created (updateObjectControls) 에서도 확실히 띄워주기
update_obj_ctrls_target = """            if (obj && obj.isPopout) {
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));"""
update_obj_ctrls_patch = """            if (obj && obj.isPopout) {
                document.getElementById('sub_toolbar').style.display = 'block';
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));"""
content = content.replace(update_obj_ctrls_target, update_obj_ctrls_patch)


# 2. 이중 컬러 피커 로직 제거 (네이티브 input type="color" 삭제)
native_picker_re = re.compile(r'const btnPopoutLineColor = document\.getElementById\(\'btn_popout_line_color\'\);\s*if \(btnPopoutLineColor\) \{[\s\S]*?canvas\.requestRenderAll\(\);\s*saveHistory\(\);\s*\}\s*\};\s*\}\);\s*\}', re.MULTILINE)
content = native_picker_re.sub('// Removed native color picker to use the global 42-color palette', content)

# 3. 틸트 시 외곽선 딱 맞게 하기 위해 네이티브 skewX, skewY 연동 & _render 커스텀 오버라이드 비활성화
# _render 안에 if (this.tiltX !== 0 || this.tiltY !== 0) 로직 전체를 날려서 OriginalImageRender 만 타게 함.
render_re = re.compile(r'if \(this\.tiltX !== 0 \|\| this\.tiltY !== 0\) \{[\s\S]*?return;\s*\}')
content = render_re.sub('// Removed custom tilt rendering to use native skewX/skewY for perfect bounding box fit', content)

# 팝아웃 속성 연동 시 skewX, skewY 같이 먹여주기
# createPopoutFromObject (index.html:7637)
tilt_create_target = """            tiltX: pSkewX ? parseInt(pSkewX.value) : 20,
            tiltY: pSkewY ? parseInt(pSkewY.value) : -30,"""
tilt_create_patch = """            tiltX: pSkewX ? parseInt(pSkewX.value) : 20,
            tiltY: pSkewY ? parseInt(pSkewY.value) : -30,
            skewX: pSkewX ? parseInt(pSkewX.value) : 20,
            skewY: pSkewY ? parseInt(pSkewY.value) : -30,"""
content = content.replace(tilt_create_target, tilt_create_patch)

# 속성창(modal_edit) applyObjectEdit (index.html:5132)
tilt_apply_target = """                    tiltX: parseInt(document.getElementById('edit_popout_skew_x').value) || 0,
                    tiltY: parseInt(document.getElementById('edit_popout_skew_y').value) || 0,"""
tilt_apply_patch = """                    tiltX: parseInt(document.getElementById('edit_popout_skew_x').value) || 0,
                    tiltY: parseInt(document.getElementById('edit_popout_skew_y').value) || 0,
                    skewX: parseInt(document.getElementById('edit_popout_skew_x').value) || 0,
                    skewY: parseInt(document.getElementById('edit_popout_skew_y').value) || 0,"""
content = content.replace(tilt_apply_target, tilt_apply_patch)

# 상단바 팝아웃 패널(popout_skew_x, popout_skew_y) bindPopoutInput 시 연동
bind_skew_target = """                    if (key === 'tiltX' || key === 'tiltY' || key === 'angle') {"""
bind_skew_patch = """                    if (key === 'tiltX') activeObj.set('skewX', val);
                    if (key === 'tiltY') activeObj.set('skewY', val);
                    if (key === 'tiltX' || key === 'tiltY' || key === 'angle') {"""
content = content.replace(bind_skew_target, bind_skew_patch)

# 4. modal_edit (더블클릭 개체 속성 수정 창) 색상 적용 안되는 버그 수정
# applyObjectEdit 안에 색상 값을 배경색에서 읽어오는데 rgb를 hex로 안 바꿔서 생기는 문제일 수 있음.
# color picker가 backgroundColor로 설정하므로 rgba 형태로 들어갈 수 있는데, popoutBorderColor 등은 이를 허용함.
# 아, 'edit_popout_border_color' 버튼 등에 bindCP를 해두었으나, color_patch_code에서 btnId 파싱에 버그가 있었을 수 있음.
# color_patch_code 다시 점검: const btnId = targetColorBtn.startsWith('edit_') ? targetColorBtn.replace('_c', 'olor') : ...
# edit_popout_line_c -> edit_popout_line_color
# 맞음. 그런데 왜 "테두리색, 그림자색 변경이 안되고 있어" 라고 할까?
# 1) panel_popout 에서의 버튼 변경: btn_popout_border_color 에 클릭이벤트가 걸려서 팔레트는 뜨는데,
#    팔레트에서 색상을 고르면 팝아웃 오브젝트에 바로 적용되어야 한다.
#    위에서 추가했던 color_patch_code (index.html:3773) 확인.
color_patch_target_2 = """                    if (!targetColorBtn.startsWith('edit_')) {"""
color_patch_patch_2 = """                    if (!targetColorBtn.startsWith('edit_')) {
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
                    }"""
# 중복 추가 방지 및 확실한 적용을 위해 정규식으로 해당 블록을 덮어씀.
color_patch_re = re.compile(r'if \(\!targetColorBtn\.startsWith\(\'edit_\'\)\) \{[\s\S]*?saveHistory\(\);\s*\}\s*\}')
content = color_patch_re.sub(color_patch_patch_2, content)


with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for final adjustments.")
