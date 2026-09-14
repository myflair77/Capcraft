import os
import re

filepath = r"c:\Coding\Capcraft\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. regeneratePopoutBase 수정
old_regen_pattern = re.compile(r"window\.regeneratePopoutBase = function\(img\) \{.*?(?=const OriginalImageRender =)", re.DOTALL)

new_regen = """window.regeneratePopoutBase = function(img) {
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
            const oldOriginX = obj.originX;
            const oldOriginY = obj.originY;
            
            const borderW = img.popoutBorder !== undefined ? img.popoutBorder : 8;
            
            // 1. Draw outer border (underneath)
            if (borderW > 0) {
                obj.stroke = 'white';
                obj.strokeWidth = borderW * 2; // Outer stroke trick: double width, covered by inner mask
                obj.fill = 'white';
                obj.shadow = null;
                obj.left = cw / 2;
                obj.top = ch / 2;
                obj.originX = 'center';
                obj.originY = 'center';
                obj.render(ctx);
            }
            
            // 2. Draw inner content on a separate canvas
            const innerCanvas = document.createElement('canvas');
            innerCanvas.width = cw; innerCanvas.height = ch;
            const innerCtx = innerCanvas.getContext('2d');
            
            // Draw object mask
            obj.stroke = 'transparent';
            obj.strokeWidth = 0;
            obj.fill = 'black';
            obj.shadow = null;
            obj.left = cw / 2;
            obj.top = ch / 2;
            obj.originX = 'center';
            obj.originY = 'center';
            obj.render(innerCtx);
            
            // Composite cropped background into the mask
            innerCtx.globalCompositeOperation = 'source-in';
            innerCtx.drawImage(img._croppedBg, 0, 0);
            
            // 3. Draw inner content over the border
            ctx.globalCompositeOperation = 'source-over';
            ctx.drawImage(innerCanvas, 0, 0);
            
            // Restore object properties
            obj.stroke = oldStroke;
            obj.strokeWidth = oldWidth;
            obj.fill = oldFill;
            obj.shadow = oldShadow;
            obj.left = oldLeft;
            obj.top = oldTop;
            obj.originX = oldOriginX;
            obj.originY = oldOriginY;
            
            img._element = tCanvas;
        };

        """

content = old_regen_pattern.sub(new_regen, content)

# 2. fabric.Image.prototype._render 수정
old_render_pattern = re.compile(r"const OriginalImageRender = fabric\.Image\.prototype\._render;\s*fabric\.Image\.prototype\._render = function\(ctx\) \{.*?(?=window\.getBoundaryIntersection = function)", re.DOTALL)

new_render = """const OriginalImageRender = fabric.Image.prototype._render;
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
                    
                    // PASS 2: Tilt Y (Vertical strips from Off-screen Canvas onto final resultCanvas)
                    const resultCanvas = document.createElement('canvas');
                    resultCanvas.width = ow; resultCanvas.height = oh;
                    const resultCtx = resultCanvas.getContext('2d');
                    
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
                            resultCtx.drawImage(this._offCanvas, x, 0, 2, oh, ow/2 + new_x, oh/2 - new_h/2, new_w + 0.5, new_h);
                        }
                    } else {
                        resultCtx.drawImage(this._offCanvas, 0, 0);
                    }
                    
                    // 최종적으로 ctx에 그림자 포함해서 단 한번 그림!
                    ctx.drawImage(resultCanvas, 0, 0, ow, oh, -ow/2, -oh/2, ow, oh);
                    
                    return;
                }
            }
            OriginalImageRender.call(this, ctx);
        };

        """

content = old_render_pattern.sub(new_render, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Popout bug fixes applied successfully.")
