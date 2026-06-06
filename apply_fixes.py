import os
import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Hit detection
content = content.replace("cornerSize: 10,", "cornerSize: 10,\n                touchCornerSize: 24,")
content = content.replace("padding: 5,", "padding: 10,")
content = content.replace("targetFindTolerance: 10,", "targetFindTolerance: 15,")

# 2. SVG save button
svg_btn = '<button data-format="svg">SVG 저장</button>\n                    '
if 'data-format="svg"' not in content:
    content = content.replace('<button data-format="pdf">PDF 저장</button>', svg_btn + '<button data-format="pdf">PDF 저장</button>')

# 3. mouse:move early return
if 'if (!activeTool && !isDrawing && !multiClickDrawing) return;' not in content:
    content = content.replace("canvas.on('mouse:move', o => {", "canvas.on('mouse:move', o => {\n            if (!activeTool && !isDrawing && !multiClickDrawing) return;")

# 4. Rotation cursor & icon size
rot_cursor_old = """const rotateCursorSvg = "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><g stroke-linecap='round' stroke-linejoin='round' fill='none'><g stroke='black' stroke-width='4'><path d='M21 2v6h-6'/><path d='M21 8A9 9 0 1 1 12 3'/></g><g stroke='white' stroke-width='2'><path d='M21 2v6h-6'/><path d='M21 8A9 9 0 1 1 12 3'/></g></g></svg>";
        const rotateCursor = `url("data:image/svg+xml;utf8,${rotateCursorSvg}") 12 12, crosshair`;"""
rot_cursor_new = """const rotateCursorSvg = "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'><g stroke-linecap='round' stroke-linejoin='round' fill='none'><g stroke='black' stroke-width='4'><path d='M21 2v6h-6'/><path d='M21 8A9 9 0 1 1 12 3'/></g><g stroke='white' stroke-width='2'><path d='M21 2v6h-6'/><path d='M21 8A9 9 0 1 1 12 3'/></g></g></svg>";
        const rotateCursor = `url("data:image/svg+xml;utf8,${encodeURIComponent(rotateCursorSvg)}") 8 8, crosshair`;"""
content = content.replace(rot_cursor_old, rot_cursor_new)

rot_icon_old = """const rotateIconSvg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='11' fill='white' stroke='%233b82f6' stroke-width='2'/><path d='M15.5 12c0 1.93-1.57 3.5-3.5 3.5s-3.5-1.57-3.5-3.5 1.57-3.5 3.5-3.5v2l3.5-3-3.5-3v2c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5h-1.5z' fill='%233b82f6'/></svg>";
            const rotateImg = new Image(); rotateImg.src = rotateIconSvg;"""
rot_icon_new = """const rotateIconSvg = "data:image/svg+xml;utf8," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='18' height='18'><circle cx='12' cy='12' r='11' fill='white' stroke='#3b82f6' stroke-width='2'/><path d='M15.5 12c0 1.93-1.57 3.5-3.5 3.5s-3.5-1.57-3.5-3.5 1.57-3.5 3.5-3.5v2l3.5-3-3.5-3v2c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5h-1.5z' fill='#3b82f6'/></svg>");
            const rotateImg = new Image(); rotateImg.src = rotateIconSvg;"""
content = content.replace(rot_icon_old, rot_icon_new)

# 5. object:moving optimization
obj_moving_old = """        canvas.on('object:moving', (e) => {
            const obj = e.target; 
            obj.setCoords(); 
            
            let br = obj.getBoundingRect();
            let cw = canvas.width;
            let ch = canvas.height;
            
            if (br.width <= cw) {
                if (br.left < 0) obj.left -= br.left;
                else if (br.left + br.width > cw) obj.left -= (br.left + br.width - cw);
            }
            if (br.height <= ch) {
                if (br.top < 0) obj.top -= br.top;
                else if (br.top + br.height > ch) obj.top -= (br.top + br.height - ch);
            }
        });"""

obj_moving_new = """        canvas.on('object:moving', (e) => {
            window._isObjectMoved = true;
            const obj = e.target; 
            const cw = canvas.width;
            const ch = canvas.height;
            
            const objW = (obj.width || 0) * (obj.scaleX || 1);
            const objH = (obj.height || 0) * (obj.scaleY || 1);
            const ox = obj.originX === 'center' ? objW / 2 : (obj.originX === 'right' ? objW : 0);
            const oy = obj.originY === 'center' ? objH / 2 : (obj.originY === 'bottom' ? objH : 0);
            
            if (objW <= cw) {
                if (obj.left - ox < 0) obj.left = ox;
                else if (obj.left - ox + objW > cw) obj.left = cw - objW + ox;
            }
            if (objH <= ch) {
                if (obj.top - oy < 0) obj.top = oy;
                else if (obj.top - oy + objH > ch) obj.top = ch - objH + oy;
            }
            
            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
            } else if (obj.linkedShape) {
                const center = obj.getCenterPoint();
                obj.linkedShape.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedShape.setCoords();
            }
        });"""
content = content.replace(obj_moving_old, obj_moving_new)

# 6. syncLinked removal (already inline now)
content = re.sub(r'function syncLinked.*?}\s+}', '', content, flags=re.DOTALL)
content = content.replace('syncLinked();', '')

# 7. objectCaching: false removal from finalized objects
# finalized objects usually have `selectable: true` and no `isTemp`.
content = re.sub(r'(newBody\s*=\s*new\s*fabric\.Path.*?)objectCaching:\s*false,?\s*(.*?})', r'\1\2', content)
content = re.sub(r'(newObj\s*=\s*new\s*fabric\.Path.*?)objectCaching:\s*false,?\s*(.*?})', r'\1\2', content)
content = content.replace("e.path.set({ selectable: true, isTemp: false, objectCaching: false });", "e.path.set({ selectable: true, isTemp: false });")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixes applied.")
