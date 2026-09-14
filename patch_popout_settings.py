import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 환경 설정 HTML 삽입 ("이모티콘 설정" 앞)
ui_html = """
        <div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px; color: var(--accent-blue);">팝 아웃 설정</div>
        <div class="setting-group"
            style="margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; font-size: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <label style="display:flex; align-items:center; gap:5px; margin:0;"><input type="checkbox" id="set_popout_line_toggle" checked> 연결선 표시</label>
                <span>연결선 색상:</span>
                <div id="set_popout_line_color" class="color-btn" style="background-color: #555555;"></div>
                <span>연결선 두께:</span> <input type="number" id="set_popout_line_weight" value="4" min="1" max="20" style="width:40px;">
            </div>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span>개체 기본 회전:</span> <input type="number" id="set_popout_angle" value="10.0" min="0.0" max="359.9" step="0.1" style="width:55px;">
                <span>가로축 회전:</span> <input type="number" id="set_popout_skew_x" value="20" min="-45" max="45" style="width:45px;">
                <span>세로축 회전:</span> <input type="number" id="set_popout_skew_y" value="-30" min="-45" max="45" style="width:45px;">
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>테두리 색상:</span>
                <div id="set_popout_border_color" class="color-btn" style="background-color: #ffffff;"></div>
                <span>테두리 두께:</span> <input type="number" id="set_popout_border" value="10" min="0" max="30" style="width:40px;">
                <span>그림자 색상:</span>
                <div id="set_popout_shadow_color" class="color-btn" style="background-color: #000000;"></div>
                <span>그림자 강도:</span> <input type="number" id="set_popout_shadow" value="50" min="0" max="100" style="width:40px;">
            </div>
        </div>

        <div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px; color: var(--accent-blue);">이모티콘 설정</div>"""

content = content.replace(
    '<div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px; color: var(--accent-blue);">이모티콘 설정</div>',
    ui_html
)

# 2. color picker 이벤트 바인딩 추가
bind_insert = "bindCP('set_txt_color', 'set_text'); bindCP('set_txt_bg_color', 'set_text_bg');\n        bindCP('set_popout_line_color', 'set_popout_line'); bindCP('set_popout_border_color', 'set_popout_border_c'); bindCP('set_popout_shadow_color', 'set_popout_shadow_c');"
content = content.replace(
    "bindCP('set_txt_color', 'set_text'); bindCP('set_txt_bg_color', 'set_text_bg');",
    bind_insert
)

# 3. collectSettings에 id 추가
# settingsIds = [ ..., 'set_arrow_size',
content = content.replace(
    "'set_arrow_size',",
    "'set_arrow_size', 'set_popout_line_toggle', 'set_popout_line_weight', 'set_popout_angle', 'set_popout_skew_x', 'set_popout_skew_y', 'set_popout_border', 'set_popout_shadow',"
)

# colorIds = [ ..., 'set_pen_bg_color'
content = content.replace(
    "'set_shape_stroke_color', 'set_shape_fill_color', 'set_pen_bg_color'",
    "'set_shape_stroke_color', 'set_shape_fill_color', 'set_pen_bg_color', 'set_popout_line_color', 'set_popout_border_color', 'set_popout_shadow_color'"
)


# 4. regeneratePopoutBase 컬러 속성 추가
old_regen_border = """const borderW = img.popoutBorder !== undefined ? img.popoutBorder : 8;
            
            // 1. Draw outer border (underneath)
            if (borderW > 0) {
                obj.stroke = 'white';
                obj.strokeWidth = borderW * 2; // Outer stroke trick: double width, covered by inner mask
                obj.fill = 'white';"""

new_regen_border = """const borderW = img.popoutBorder !== undefined ? img.popoutBorder : 10;
            const borderC = img.popoutBorderColor || '#ffffff';
            
            // 1. Draw outer border (underneath)
            if (borderW > 0) {
                obj.stroke = borderC;
                obj.strokeWidth = borderW * 2; // Outer stroke trick: double width, covered by inner mask
                obj.fill = borderC;"""
content = content.replace(old_regen_border, new_regen_border)


# 5. applyPopoutTilt 섀도 컬러 속성 추가
old_tilt = """if (obj.shadow) {
                obj.shadow.offsetX = sX;
                obj.shadow.offsetY = sY;
                obj.shadow.blur = shadowIntensity;
                obj.shadow.color = `rgba(0,0,0,${Math.min(0.8, shadowIntensity/80)})`;
            }"""

new_tilt = """if (obj.shadow) {
                obj.shadow.offsetX = sX;
                obj.shadow.offsetY = sY;
                obj.shadow.blur = shadowIntensity;
                
                const shadowC = obj.popoutShadowColor || '#000000';
                let alpha = Math.min(0.8, shadowIntensity/80);
                let finalColor = `rgba(0,0,0,${alpha})`;
                if (shadowC.startsWith('rgba')) {
                    finalColor = shadowC.replace(/[\d\.]+\)$/, `${alpha})`);
                } else if (shadowC.startsWith('rgb')) {
                    finalColor = shadowC.replace('rgb', 'rgba').replace(')', `, ${alpha})`);
                } else if (shadowC.startsWith('#')) {
                    let hex = shadowC.replace('#', '');
                    if (hex.length === 3) hex = hex.split('').map(c => c+c).join('');
                    let r = parseInt(hex.substring(0,2), 16) || 0;
                    let g = parseInt(hex.substring(2,4), 16) || 0;
                    let b = parseInt(hex.substring(4,6), 16) || 0;
                    finalColor = `rgba(${r},${g},${b},${alpha})`;
                }
                obj.shadow.color = finalColor;
            }"""
content = content.replace(old_tilt, new_tilt)


# 6. createPopoutFromObject 에 기본값 주입
old_create_popout = """img.set({
            left: obj.left + 50 * zoom,
            top: obj.top - 50 * zoom,
            originX: 'center',
            originY: 'center',
            shadow: new fabric.Shadow({
                color: 'rgba(0,0,0,0.7)',
                blur: 50,
                offsetX: 0,
                offsetY: 25
            }),
            tiltX: 0,
            tiltY: 0,
            scaleX: 1.0,
            scaleY: 1.0,
            hasControls: false,
            hasBorders: false,
            objectCaching: false,
            isPopout: true,
            showConnectionLine: true,
            linkedOriginal: obj,
            popoutBorder: 8,
            popoutShadow: 50,
            popoutLineWeight: 4,
            popoutLineColor: '#94a3b8'
        });"""

new_create_popout = """
        const pLineToggle = document.getElementById('set_popout_line_toggle');
        const pLineColor = document.getElementById('set_popout_line_color');
        const pLineW = document.getElementById('set_popout_line_weight');
        const pAngle = document.getElementById('set_popout_angle');
        const pSkewX = document.getElementById('set_popout_skew_x');
        const pSkewY = document.getElementById('set_popout_skew_y');
        const pBorderC = document.getElementById('set_popout_border_color');
        const pBorder = document.getElementById('set_popout_border');
        const pShadowC = document.getElementById('set_popout_shadow_color');
        const pShadow = document.getElementById('set_popout_shadow');

        img.set({
            left: obj.left + 50 * zoom,
            top: obj.top - 50 * zoom,
            originX: 'center',
            originY: 'center',
            shadow: new fabric.Shadow({
                color: pShadowC ? pShadowC.style.backgroundColor : '#000000',
                blur: pShadow ? parseInt(pShadow.value) : 50,
                offsetX: 0,
                offsetY: 25
            }),
            angle: pAngle ? parseFloat(pAngle.value) : 10.0,
            tiltX: pSkewX ? parseInt(pSkewX.value) : 20,
            tiltY: pSkewY ? parseInt(pSkewY.value) : -30,
            scaleX: 1.0,
            scaleY: 1.0,
            hasControls: false,
            hasBorders: false,
            objectCaching: false,
            isPopout: true,
            showConnectionLine: pLineToggle ? pLineToggle.checked : true,
            linkedOriginal: obj,
            popoutBorder: pBorder ? parseInt(pBorder.value) : 10,
            popoutBorderColor: pBorderC ? pBorderC.style.backgroundColor : '#ffffff',
            popoutShadow: pShadow ? parseInt(pShadow.value) : 50,
            popoutShadowColor: pShadowC ? pShadowC.style.backgroundColor : '#000000',
            popoutLineWeight: pLineW ? parseInt(pLineW.value) : 4,
            popoutLineColor: pLineColor ? (pLineColor.style.backgroundColor || '#555555') : '#555555'
        });"""
content = content.replace(old_create_popout, new_create_popout)


with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to index.html successfully.")
