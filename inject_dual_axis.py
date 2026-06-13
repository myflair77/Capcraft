# -*- coding: utf-8 -*-
import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update toggleEdgeGlow to completely ignore popouts
old_toggle_edge = """        function toggleEdgeGlow(e, isActive) {
            const objs = e.selected || e.deselected || [];
            objs.forEach(obj => {"""
new_toggle_edge = """        function toggleEdgeGlow(e, isActive) {
            const objs = e.selected || e.deselected || [];
            objs.forEach(obj => {
                if (obj.isPopout) {
                    obj.set({ hasBorders: false, hasControls: false });
                    return;
                }"""
content = content.replace(old_toggle_edge, new_toggle_edge)


# 2. Update panel_popout UI
old_panel_popout = """        <div id="panel_popout" class="sub-panel" style="gap:10px;">
            <label style="font-size: 12px; color: var(--text-color); display:flex; align-items:center; gap:5px; cursor:pointer;">
                <input type="checkbox" id="popout_line_toggle" checked> 연결선 표시
            </label>
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="font-size:12px; color:var(--text-color);">가로 회전:</span>
                <input type="number" id="popout_skew_x" min="-45" max="45" value="0" style="width: 50px;">
            </div>
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="font-size:12px; color:var(--text-color);">세로 회전:</span>
                <input type="number" id="popout_skew_y" min="-45" max="45" value="0" style="width: 50px;">
            </div>
        </div>"""

new_panel_popout = """        <div id="panel_popout" class="sub-panel" style="gap:10px;">
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
            <div style="display:flex; align-items:center; gap:5px;" title="테두리 강조">
                <span style="font-size:12px; color:var(--text-color);">테두리:</span>
                <input type="number" id="popout_border" min="0" max="30" value="8" style="width: 35px;">
            </div>
            <div style="display:flex; align-items:center; gap:5px;" title="그림자 강조">
                <span style="font-size:12px; color:var(--text-color);">그림자:</span>
                <input type="number" id="popout_shadow" min="0" max="100" value="50" style="width: 40px;">
            </div>
        </div>"""
content = content.replace(old_panel_popout, new_panel_popout)


# 3. Update createPopoutFromObject & Rendering Logic
# We replace from `window.applyPopoutTilt = function(obj) {` down to `window.getBoundaryIntersection = function`
old_render_block_pattern = re.compile(r"window\.applyPopoutTilt = function\(obj\) \{.*?(?=window\.getBoundaryIntersection = function)", re.DOTALL)

new_render_block = """window.applyPopoutTilt = function(obj) {
            const tiltX = obj.tiltX || 0;
            const tiltY = obj.tiltY || 0;
            const radX = tiltX * Math.PI / 180;
            const radY = tiltY * Math.PI / 180;
            
            const shadowIntensity = obj.popoutShadow !== undefined ? obj.popoutShadow : 50;
            const maxShadowShift = shadowIntensity * 0.8;
            
            // 그림자가 앞/위로 튀어나오지 않고 항상 자연스럽게 아래/우측으로 깔리도록 절대적인 Base 오프셋 지정
            let baseOffsetX = shadowIntensity * 0.3;
            let baseOffsetY = shadowIntensity * 0.5;
            
            let sX = baseOffsetX + Math.sin(radY) * maxShadowShift;
            let sY = baseOffsetY + Math.sin(radX) * maxShadowShift;
            
            // 음수 방지 (항상 개체 뒤/아래로)
            if (sY < 0) sY = 0;
            if (sX < -baseOffsetX) sX = -baseOffsetX;
            
            if (obj.shadow) {
                obj.shadow.offsetX = sX;
                obj.shadow.offsetY = sY;
                obj.shadow.blur = shadowIntensity;
                obj.shadow.color = `rgba(0,0,0,${Math.min(0.8, shadowIntensity/80)})`;
            }
            obj.dirty = true;
        };

        window.regeneratePopoutBase = function(img) {
            if (!img._croppedBg) return;
            const cw = img.width;
            const ch = img.height;
            const tCanvas = document.createElement('canvas');
            tCanvas.width = cw; tCanvas.height = ch;
            const ctx = tCanvas.getContext('2d');
            
            const obj = img.linkedOriginal;
            if (!obj) return;
            
            const oldStroke = obj.stroke;
            const oldWidth = obj.strokeWidth;
            const oldFill = obj.fill;
            const oldShadow = obj.shadow;
            const oldLeft = obj.left;
            const oldTop = obj.top;
            
            // 1. Draw solid shape mask
            obj.stroke = 'transparent';
            obj.strokeWidth = 0;
            obj.fill = 'black';
            obj.shadow = null;
            obj.left = cw/2;
            obj.top = ch/2;
            obj.render(ctx);
            
            // 2. Composite background inside shape
            ctx.globalCompositeOperation = 'source-in';
            ctx.drawImage(img._croppedBg, 0, 0);
            
            // 3. Draw border on top
            const borderW = img.popoutBorder !== undefined ? img.popoutBorder : 8;
            if (borderW > 0) {
                ctx.globalCompositeOperation = 'source-over';
                obj.fill = 'transparent';
                obj.stroke = 'white';
                obj.strokeWidth = borderW;
                obj.render(ctx);
            }
            
            obj.stroke = oldStroke;
            obj.strokeWidth = oldWidth;
            obj.fill = oldFill;
            obj.shadow = oldShadow;
            obj.left = oldLeft;
            obj.top = oldTop;
            
            img._element = tCanvas;
        };

        const OriginalImageRender = fabric.Image.prototype._render;
        fabric.Image.prototype._render = function(ctx) {
            if (this.isPopout) {
                // 실시간 보더 변경 반영
                if (this._lastBorder !== this.popoutBorder) {
                    regeneratePopoutBase(this);
                    this._lastBorder = this.popoutBorder;
                }
                
                if (this.tiltX !== 0 || this.tiltY !== 0) {
                    const w = this.width;
                    const h = this.height;
                    const tiltX = this.tiltX || 0;
                    const tiltY = this.tiltY || 0;
                    const D = Math.max(w, h) * 1.5;
                    
                    if (!this._offCanvas) {
                        this._offCanvas = document.createElement('canvas');
                        this._offCtx = this._offCanvas.getContext('2d');
                    }
                    
                    const margin = Math.max(w, h) * 0.5;
                    const ow = w + margin * 2;
                    const oh = h + margin * 2;
                    if (this._offCanvas.width !== ow) {
                        this._offCanvas.width = ow;
                        this._offCanvas.height = oh;
                    } else {
                        this._offCtx.clearRect(0, 0, ow, oh);
                    }
                    
                    // PASS 1: Tilt X (Horizontal strips onto Off-screen Canvas)
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
                            this._offCtx.drawImage(this._element, 0, y, w, 2, ow/2 - new_w/2, oh/2 + new_y, new_w, new_h + 0.5);
                        }
                    } else {
                        this._offCtx.drawImage(this._element, ow/2 - w/2, oh/2 - h/2, w, h);
                    }
                    
                    // PASS 2: Tilt Y (Vertical strips from Off-screen Canvas onto Final Context)
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
                            ctx.drawImage(this._offCanvas, x, 0, 2, oh, new_x, -new_h/2, new_w + 0.5, new_h);
                        }
                    } else {
                        ctx.drawImage(this._offCanvas, 0, 0, ow, oh, -ow/2, -oh/2, ow, oh);
                    }
                    return;
                }
            }
            OriginalImageRender.call(this, ctx);
        };

        """
content = old_render_block_pattern.sub(new_render_block, content)


# 4. Modify createPopoutFromObject to cache croppedBg instead of baking
old_create_crop = """    // 3. Draw White Border
    maskCtx.globalCompositeOperation = 'source-over';
    obj.strokeWidth = 8; // Border width for popout
    obj.stroke = 'white';
    obj.fill = 'transparent';
    canvas.renderAll();
    maskCtx.drawImage(canvas.getElement(), 0, 0);
    
    // 4. Restore everything
    obj.strokeWidth = oldStrokeWidth;
    obj.stroke = oldStroke;
    obj.fill = oldFill;
    obj.shadow = oldShadow;
    canvas.backgroundImage = oldBg;
    canvas.backgroundColor = oldBgColor;
    canvas.getObjects().forEach((o, i) => { if (o !== obj) o.visible = oldVisible[i]; });
    obj.visible = oldObjVisible;
    canvas.setViewportTransform(vpt);
    canvas.renderAll();
    
    // 5. Crop
    const pad = 10;
    const br = obj.getBoundingRect(true, true);
    const cw = br.width + pad * 2;
    const ch = br.height + pad * 2;
    const cx = br.left - pad;
    const cy = br.top - pad;
    
    const croppedCanvas = document.createElement('canvas');
    croppedCanvas.width = cw;
    croppedCanvas.height = ch;
    croppedCanvas.getContext('2d').drawImage(maskCanvas, cx, cy, cw, ch, 0, 0, cw, ch);
    
    fabric.Image.fromURL(croppedCanvas.toDataURL(), function(img) {"""

new_create_crop = """    // We don't draw border here anymore. We just crop the background and save it.
    // 4. Restore everything
    obj.strokeWidth = oldStrokeWidth;
    obj.stroke = oldStroke;
    obj.fill = oldFill;
    obj.shadow = oldShadow;
    canvas.backgroundImage = oldBg;
    canvas.backgroundColor = oldBgColor;
    canvas.getObjects().forEach((o, i) => { if (o !== obj) o.visible = oldVisible[i]; });
    obj.visible = oldObjVisible;
    canvas.setViewportTransform(vpt);
    canvas.renderAll();
    
    // 5. Crop
    const pad = 40; // padding to allow dynamic border and shadow
    const br = obj.getBoundingRect(true, true);
    const cw = br.width + pad * 2;
    const ch = br.height + pad * 2;
    const cx = br.left - pad;
    const cy = br.top - pad;
    
    const croppedBgCanvas = document.createElement('canvas');
    croppedBgCanvas.width = cw;
    croppedBgCanvas.height = ch;
    croppedBgCanvas.getContext('2d').drawImage(bgCanvas, cx, cy, cw, ch, 0, 0, cw, ch);
    
    // Create a dummy transparent canvas for the image element initially
    const dummyCanvas = document.createElement('canvas');
    dummyCanvas.width = cw; dummyCanvas.height = ch;
    
    fabric.Image.fromURL(dummyCanvas.toDataURL(), function(img) {"""
content = content.replace(old_create_crop, new_create_crop)


# 5. Attach variables to img on creation
old_img_attach = """            scaleX: 1.0,
            scaleY: 1.0,
            hasControls: false,
            hasBorders: false,
            objectCaching: false,
            isPopout: true,
            showConnectionLine: true,
            linkedOriginal: obj
        });"""

new_img_attach = """            scaleX: 1.0,
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
        });
        
        img._croppedBg = croppedBgCanvas;
        regeneratePopoutBase(img); // Bake the first image
        """
content = content.replace(old_img_attach, new_img_attach)


# 6. Update events and setup Panel bindings
old_slider_events = """        document.getElementById('popout_skew_x').addEventListener('input', function(e) {
            const obj = canvas.getActiveObject();
            if (obj && obj.isPopout) {
                obj.tiltX = parseInt(this.value);
                applyPopoutTilt(obj);
                updatePopoutLine(obj);
                canvas.requestRenderAll();
            }
        });

        document.getElementById('popout_skew_y').addEventListener('input', function(e) {
            const obj = canvas.getActiveObject();
            if (obj && obj.isPopout) {
                obj.tiltY = parseInt(this.value);
                applyPopoutTilt(obj);
                updatePopoutLine(obj);
                canvas.requestRenderAll();
            }
        });"""

new_slider_events = """        function bindPopoutInput(id, propName, parser, callback) {
            document.getElementById(id).addEventListener('input', function(e) {
                const obj = canvas.getActiveObject();
                if (obj && obj.isPopout) {
                    obj[propName] = parser(this.value);
                    if (callback) callback(obj);
                    canvas.requestRenderAll();
                }
            });
        }
        
        bindPopoutInput('popout_skew_x', 'tiltX', parseInt, applyPopoutTilt);
        bindPopoutInput('popout_skew_y', 'tiltY', parseInt, applyPopoutTilt);
        bindPopoutInput('popout_border', 'popoutBorder', parseInt, null);
        bindPopoutInput('popout_shadow', 'popoutShadow', parseInt, applyPopoutTilt);
        bindPopoutInput('popout_line_weight', 'popoutLineWeight', parseInt, obj => {
            if (obj.linkedLine) obj.linkedLine.strokeWidth = obj.popoutLineWeight;
        });
        
        document.getElementById('popout_line_toggle').addEventListener('change', function(e) {
            const obj = canvas.getActiveObject();
            if (obj && obj.isPopout) {
                obj.showConnectionLine = this.checked;
                updatePopoutLine(obj);
                canvas.requestRenderAll();
            }
        });
        
        // Connect Line Color Picker (we reuse the native color picker logic or direct input)
        document.getElementById('btn_popout_line_color').addEventListener('click', function(e) {
            const btn = this;
            const input = document.createElement('input');
            input.type = 'color';
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
        
        function rgb2hex(rgb) {
            if (!rgb) return null;
            if (rgb.startsWith('#')) return rgb;
            const res = rgb.match(/\d+/g);
            if (!res || res.length < 3) return null;
            return "#" + ((1 << 24) + (parseInt(res[0]) << 16) + (parseInt(res[1]) << 8) + parseInt(res[2])).toString(16).slice(1);
        }
        """
content = content.replace(old_slider_events, new_slider_events)

# 7. Update panel sync on selection
old_panel_active = """                document.getElementById('popout_skew_x').value = obj.tiltX || 0;
                document.getElementById('popout_skew_y').value = obj.tiltY || 0;
            }"""
new_panel_active = """                document.getElementById('popout_skew_x').value = obj.tiltX || 0;
                document.getElementById('popout_skew_y').value = obj.tiltY || 0;
                document.getElementById('popout_line_toggle').checked = obj.showConnectionLine;
                document.getElementById('popout_line_weight').value = obj.popoutLineWeight || 4;
                document.getElementById('btn_popout_line_color').style.backgroundColor = obj.popoutLineColor || '#94a3b8';
                document.getElementById('popout_border').value = obj.popoutBorder !== undefined ? obj.popoutBorder : 8;
                document.getElementById('popout_shadow').value = obj.popoutShadow !== undefined ? obj.popoutShadow : 50;
            }"""
content = content.replace(old_panel_active, new_panel_active)

# 8. Fix updatePopoutLine stroke width/color on creation
old_line_create = """        const line = new fabric.Line([0,0,0,0], {
            stroke: '#94a3b8',
            strokeWidth: 4,
            strokeDashArray: null,"""
new_line_create = """        const line = new fabric.Line([0,0,0,0], {
            stroke: img.popoutLineColor,
            strokeWidth: img.popoutLineWeight,
            strokeDashArray: null,"""
content = content.replace(old_line_create, new_line_create)


with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Dual-axis rendering and UI expansion successfully injected!")
