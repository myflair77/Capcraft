# -*- coding: utf-8 -*-
import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove isPopout restriction from toggleEdgeGlow
old_toggle_edge = """        function toggleEdgeGlow(e, isActive) {
            const objs = e.selected || e.deselected || [];
            objs.forEach(obj => {
                if (obj.isPopout) {
                    obj.set({ hasBorders: false, hasControls: false });
                    return;
                }
                obj.set({"""
new_toggle_edge = """        function toggleEdgeGlow(e, isActive) {
            const objs = e.selected || e.deselected || [];
            objs.forEach(obj => {
                obj.set({"""
content = content.replace(old_toggle_edge, new_toggle_edge)

# 2. Fix regeneratePopoutBase (fill with solid color before bg canvas)
old_regen = """            // 2. Composite background inside shape
            ctx.globalCompositeOperation = 'source-in';
            ctx.drawImage(img._croppedBg, 0, 0);"""
new_regen = """            // 2. Composite background inside shape
            ctx.globalCompositeOperation = 'source-in';
            ctx.fillStyle = canvas.backgroundColor || '#ffffff';
            ctx.fillRect(0, 0, cw, ch);
            ctx.globalCompositeOperation = 'source-over';
            ctx.drawImage(img._croppedBg, 0, 0);"""
content = content.replace(old_regen, new_regen)

# 3. Fix createPopoutFromObject Viewport Transform timing (move setViewportTransform to END)
old_crop_vpt = """    canvas.getObjects().forEach((o, i) => { if (o !== obj) o.visible = oldVisible[i]; });
    obj.visible = oldObjVisible;
    canvas.setViewportTransform(vpt);
    canvas.renderAll();
    
    // 5. Crop
    const pad = 40; // padding to allow dynamic border and shadow
    const br = obj.getBoundingRect(true, true);"""
new_crop_vpt = """    canvas.getObjects().forEach((o, i) => { if (o !== obj) o.visible = oldVisible[i]; });
    obj.visible = oldObjVisible;
    canvas.renderAll();
    
    // 5. Crop
    const pad = 40; // padding to allow dynamic border and shadow
    const br = obj.getBoundingRect(true, true);"""
content = content.replace(old_crop_vpt, new_crop_vpt)

old_img_create = """        img._croppedBg = croppedBgCanvas;
        regeneratePopoutBase(img); // Bake the first image"""
new_img_create = """        img._croppedBg = croppedBgCanvas;
        regeneratePopoutBase(img); // Bake the first image
        
        // NOW restore viewport
        canvas.setViewportTransform(vpt);
        canvas.requestRenderAll();"""
content = content.replace(old_img_create, new_img_create)

# 4. Inject bindPopoutInput robustly!
# Find the exact slider listeners and replace them using regex
slider_events_regex = re.compile(r"document\.getElementById\('popout_skew_x'\)\.addEventListener\('input'.*?canvas\.requestRenderAll\(\);\s*\}\s*\}\);", re.DOTALL)

new_bind_inputs = """function bindPopoutInput(id, propName, parser, callback) {
            document.getElementById(id).addEventListener('input', function(e) {
                const obj = canvas.getActiveObject();
                if (obj && obj.isPopout) {
                    obj[propName] = parser(this.value);
                    if (callback) callback(obj);
                    canvas.requestRenderAll();
                }
            });
        }
        
        bindPopoutInput('popout_skew_x', 'tiltX', parseFloat, applyPopoutTilt);
        bindPopoutInput('popout_skew_y', 'tiltY', parseFloat, applyPopoutTilt);
        bindPopoutInput('popout_border', 'popoutBorder', parseFloat, null);
        bindPopoutInput('popout_shadow', 'popoutShadow', parseFloat, applyPopoutTilt);
        bindPopoutInput('popout_line_weight', 'popoutLineWeight', parseFloat, obj => {
            if (obj.linkedLine) {
                obj.linkedLine.strokeWidth = obj.popoutLineWeight;
            }
        });
        
        const popoutLineToggle = document.getElementById('popout_line_toggle');
        if (popoutLineToggle) {
            popoutLineToggle.addEventListener('change', function(e) {
                const obj = canvas.getActiveObject();
                if (obj && obj.isPopout) {
                    obj.showConnectionLine = this.checked;
                    updatePopoutLine(obj);
                    canvas.requestRenderAll();
                }
            });
        }
        
        const btnPopoutLineColor = document.getElementById('btn_popout_line_color');
        if (btnPopoutLineColor) {
            btnPopoutLineColor.addEventListener('click', function(e) {
                const btn = this;
                const input = document.createElement('input');
                input.type = 'color';
                
                function rgb2hex(rgb) {
                    if (!rgb) return null;
                    if (rgb.startsWith('#')) return rgb;
                    const res = rgb.match(/\d+/g);
                    if (!res || res.length < 3) return null;
                    return "#" + ((1 << 24) + (parseInt(res[0]) << 16) + (parseInt(res[1]) << 8) + parseInt(res[2])).toString(16).slice(1);
                }
                
                input.value = rgb2hex(btn.style.backgroundColor) || '#94a3b8';
                input.oninput = function() {
                    btn.style.backgroundColor = input.value;
                    const obj = canvas.getActiveObject();
                    if (obj && obj.isPopout && obj.linkedLine) {
                        obj.popoutLineColor = input.value;
                        obj.linkedLine.stroke = input.value;
                        canvas.requestRenderAll();
                    }
                };
                input.click();
            });
        }"""
content = slider_events_regex.sub(new_bind_inputs, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Bug fixes applied successfully!")
