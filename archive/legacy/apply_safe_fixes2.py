import os

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. mouse:move early return
content = content.replace("canvas.on('mouse:move', o => {", "canvas.on('mouse:move', o => {\n            if (!activeTool && !isDrawing && !multiClickDrawing) return;")

# 2. object:moving optimizations (use proper string replacement)
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

# 3. syncLinked function removal
import re
# We just replace the function call syncLinked() to nothing since we inlined it
content = content.replace("syncLinked();", "")

# 4. Finalized object caching
content = content.replace("objectCaching: false, isArrowBody: true }", "isArrowBody: true }")
content = content.replace("isTemp: false, objectCaching: false }", "isTemp: false, objectCaching: true }")
# Find explicit occurrences where objectCaching: false is applied to selectable: true shapes
content = re.sub(r'selectable:\s*true,\s*evented:\s*true,\s*objectCaching:\s*false', 'selectable: true, evented: true, objectCaching: true', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Safe fixes 2 applied.")
