import re
import os

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update bindPopoutInput for popout_border
content = content.replace(
    "bindPopoutInput('popout_border', 'popoutBorder', parseFloat, null);",
    "bindPopoutInput('popout_border', 'popoutBorder', parseFloat, regeneratePopoutBase);"
)

# 2. Fix sub_toolbar alignment in updateObjectControls
old_sub_align = """                sub.style.top = (tbRect.bottom + 10) + 'px';
                sub.style.left = '50%';
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));"""

new_sub_align = """                sub.style.top = (tbRect.bottom + 10) + 'px';
                const textBtn = document.getElementById('btn_text');
                if (textBtn) {
                    const textRect = textBtn.getBoundingClientRect();
                    sub.style.left = textRect.left + 'px';
                    sub.style.transform = 'none';
                } else {
                    sub.style.left = '50%';
                    sub.style.transform = 'translateX(-50%)';
                }
                document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));"""
content = content.replace(old_sub_align, new_sub_align)

# 3. Modify applyPopoutTilt to remove skewX/skewY
old_apply = """        window.applyPopoutTilt = function(obj) {
            const tiltX = obj.tiltX || 0;
            const tiltY = obj.tiltY || 0;
            obj.skewX = tiltX;
            obj.skewY = tiltY;
            const radX = tiltX * Math.PI / 180;
            const radY = tiltY * Math.PI / 180;"""

new_apply = """        window.applyPopoutTilt = function(obj) {
            const tiltX = obj.tiltX || 0;
            const tiltY = obj.tiltY || 0;
            obj.skewX = 0;
            obj.skewY = 0;
            const radX = tiltX * Math.PI / 180;
            const radY = tiltY * Math.PI / 180;"""
content = content.replace(old_apply, new_apply)

# Add regeneratePopoutBase call in applyPopoutTilt if it isn't there
old_apply_end = """                obj.shadow.blur = shadowIntensity;
                obj.shadow.color = `rgba(0,0,0,${Math.min(0.8, shadowIntensity/80)})`;
            }
            obj.dirty = true;
        };"""
new_apply_end = """                obj.shadow.blur = shadowIntensity;
                obj.shadow.color = `rgba(0,0,0,${Math.min(0.8, shadowIntensity/80)})`;
            }
            obj.dirty = true;
            regeneratePopoutBase(obj);
        };"""
content = content.replace(old_apply_end, new_apply_end)


# 4. Modify regeneratePopoutBase to handle 3D perspective and precise cropping
old_regen_pattern = re.compile(r"window\.regeneratePopoutBase = function\(img\) \{.*?\};(?=\s*const OriginalImageRender)", re.DOTALL)

new_regen = """window.regeneratePopoutBase = function(img) {
            if (!img._croppedBg) return;
            const borderW = img.popoutBorder !== undefined ? img.popoutBorder : 10;
            const pad = borderW + 2; 
            
            const baseW = img._croppedBg.width;
            const baseH = img._croppedBg.height;
            const cw = baseW + pad * 2;
            const ch = baseH + pad * 2;
            
            const flatCanvas = document.createElement('canvas');
            flatCanvas.width = cw; flatCanvas.height = ch;
            const flatCtx = flatCanvas.getContext('2d');
            
            const obj = img.linkedOriginal;
            if (!obj) return;
            
            const oldStroke = obj.stroke;
            const oldWidth = obj.strokeWidth;
            const oldFill = obj.fill;
            const oldShadow = obj.shadow;
            const oldLeft = obj.left;
            const oldTop = obj.top;
            const oldOriginX = obj.originX;
            const oldOriginY = obj.originY;
            
            obj.stroke = 'transparent';
            obj.strokeWidth = 0;
            obj.fill = 'black';
            obj.shadow = null;
            obj.left = cw / 2;
            obj.top = ch / 2;
            obj.originX = 'center';
            obj.originY = 'center';
            obj.render(flatCtx);
            
            flatCtx.globalCompositeOperation = 'source-in';
            flatCtx.drawImage(img._croppedBg, pad, pad);
            
            if (borderW > 0) {
                flatCtx.globalCompositeOperation = 'source-over';
                obj.fill = 'transparent';
                obj.stroke = img.popoutBorderColor || 'white';
                obj.strokeWidth = borderW;
                obj.render(flatCtx);
            }
            
            obj.stroke = oldStroke;
            obj.strokeWidth = oldWidth;
            obj.fill = oldFill;
            obj.shadow = oldShadow;
            obj.left = oldLeft;
            obj.top = oldTop;
            obj.originX = oldOriginX;
            obj.originY = oldOriginY;
            
            const tiltX = img.tiltX || 0;
            const tiltY = img.tiltY || 0;
            
            let finalCanvas = flatCanvas;
            let ow = cw, oh = ch;
            
            if (tiltX !== 0 || tiltY !== 0) {
                const w = cw;
                const h = ch;
                const D = Math.max(w, h) * 1.5;
                const margin = Math.max(w, h) * 0.5;
                ow = w + margin * 2;
                oh = h + margin * 2;
                
                const offCanvas = document.createElement('canvas');
                offCanvas.width = ow; offCanvas.height = oh;
                const offCtx = offCanvas.getContext('2d');
                
                if (tiltX !== 0) {
                    const radX = tiltX * Math.PI / 180;
                    for (let y = 0; y < h; y += 2) {
                        let dy = y - h/2;
                        let z = dy * Math.sin(radX);
                        let scale = D / (D - z);
                        let new_y = dy * Math.cos(radX) * scale;
                        let new_w = w * scale;
                        let dy_next = (y + 2) - h/2;
                        let z_next = dy_next * Math.sin(radX);
                        let scale_next = D / (D - z_next);
                        let new_y_next = dy_next * Math.cos(radX) * scale_next;
                        let new_h = new_y_next - new_y;
                        offCtx.drawImage(flatCanvas, 0, y, w, 2, ow/2 - new_w/2, oh/2 + new_y, new_w, new_h + 0.5);
                    }
                } else {
                    offCtx.drawImage(flatCanvas, ow/2 - w/2, oh/2 - h/2, w, h);
                }
                
                finalCanvas = document.createElement('canvas');
                finalCanvas.width = ow; finalCanvas.height = oh;
                const finalCtx = finalCanvas.getContext('2d');
                
                if (tiltY !== 0) {
                    const radY = tiltY * Math.PI / 180;
                    for (let x = 0; x < ow; x += 2) {
                        let dx = x - ow/2;
                        let z = dx * Math.sin(radY);
                        let scale = D / (D + z);
                        let new_x = dx * Math.cos(radY) * scale;
                        let new_h = oh * scale;
                        let dx_next = (x + 2) - ow/2;
                        let z_next = dx_next * Math.sin(radY);
                        let scale_next = D / (D + z_next);
                        let new_x_next = dx_next * Math.cos(radY) * scale_next;
                        let new_w = new_x_next - new_x;
                        finalCtx.drawImage(offCanvas, x, 0, 2, oh, ow/2 + new_x, oh/2 - new_h/2, new_w + 0.5, new_h);
                    }
                } else {
                    finalCtx.drawImage(offCanvas, 0, 0, ow, oh);
                }
            }
            
            // Trim transparent pixels
            const pixels = finalCanvas.getContext('2d').getImageData(0, 0, ow, oh);
            let l = ow, r = 0, t = oh, b = 0;
            const data = pixels.data;
            for(let y=0; y<oh; y++) {
                for(let x=0; x<ow; x++) {
                    if(data[(y*ow+x)*4+3] > 0) {
                        if(x < l) l = x; if(x > r) r = x;
                        if(y < t) t = y; if(y > b) b = y;
                    }
                }
            }
            
            if (l > r || t > b) {
                img._element = finalCanvas;
                img.set({width: ow, height: oh});
                return;
            }
            
            const trimmedW = r - l + 1;
            const trimmedH = b - t + 1;
            const trimmedCanvas = document.createElement('canvas');
            trimmedCanvas.width = trimmedW; trimmedCanvas.height = trimmedH;
            trimmedCanvas.getContext('2d').drawImage(finalCanvas, l, t, trimmedW, trimmedH, 0, 0, trimmedW, trimmedH);
            
            const shiftX = (l + r) / 2 - ow / 2;
            const shiftY = (t + b) / 2 - oh / 2;
            
            if (img._baseLeft === undefined) {
                img._baseLeft = img.left;
                img._baseTop = img.top;
            }
            img._currentShiftX = shiftX;
            img._currentShiftY = shiftY;
            
            img.set({
                left: img._baseLeft + shiftX,
                top: img._baseTop + shiftY,
                width: trimmedW,
                height: trimmedH
            });
            img._element = trimmedCanvas;
            img.setCoords();
        };"""
content = old_regen_pattern.sub(new_regen, content)


# 5. Add object:moving hook for popouts
hook_str = """        canvas.on('object:moving', (e) => {
            if (e.target && e.target.isPopout) {
                e.target._baseLeft = e.target.left - (e.target._currentShiftX || 0);
                e.target._baseTop = e.target.top - (e.target._currentShiftY || 0);
            }
        });"""

if "e.target._baseLeft = e.target.left" not in content:
    content = content.replace(
        "canvas.on('object:added', (e) => {",
        hook_str + "\n\n        canvas.on('object:added', (e) => {"
    )

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Popout bugs fixed successfully.")
