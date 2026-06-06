import codecs
import re

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# 1. Update hit box properties (sizeX, sizeY)
content = re.sub(
    r"cornerSize:\s*100,\s*touchCornerSize:\s*100,\s*transparentCorners:\s*false",
    r"sizeX: 60, sizeY: 60, cornerSize: 60, touchCornerSize: 60, transparentCorners: false",
    content
)

# 2. Text creation and constraint logic in btn_add_text_to_shape
old_text_init = """            const textObj = new fabric.Textbox('내용 입력', {
                left: center.x,
                top: center.y,
                originX: 'center',
                originY: 'center',
                width: obj.width * obj.scaleX - 20,
                fontSize: txtSize,
                fill: txtColor,
                textBackgroundColor: txtBgColor === 'transparent' ? '' : txtBgColor,
                fontWeight: isBold ? 'bold' : 'normal',
                fontStyle: isItalic ? 'italic' : 'normal',
                underline: isUnderline,
                textAlign: textAlign,
                fontFamily: 'Pretendard',
                editable: true,
                hasControls: false,
                hasBorders: false,
                selectable: true
            });"""

new_text_init = """            let initialTextW = obj.width * obj.scaleX - 20;
            if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                initialTextW = (obj.width * obj.scaleX) / 1.5;
            } else if (obj.type === 'ellipse') {
                initialTextW = (obj.width * obj.scaleX) / 1.2;
            }
            
            const textObj = new fabric.Textbox('내용 입력', {
                left: center.x,
                top: center.y,
                originX: 'center',
                originY: 'center',
                width: initialTextW,
                fontSize: txtSize,
                fill: txtColor,
                textBackgroundColor: txtBgColor === 'transparent' ? '' : txtBgColor,
                fontWeight: isBold ? 'bold' : 'normal',
                fontStyle: isItalic ? 'italic' : 'normal',
                underline: isUnderline,
                textAlign: textAlign,
                fontFamily: 'Pretendard',
                editable: true,
                hasControls: false,
                hasBorders: false,
                selectable: false,
                evented: false
            });
            
            textObj.on('editing:exited', function() {
                this.evented = false;
                this.selectable = false;
                if (this.linkedShape) {
                    canvas.setActiveObject(this.linkedShape);
                }
            });"""
content = content.replace(old_text_init, new_text_init)

old_text_changed = """                let newW = Math.max(baseW, reqW);
                let newH = Math.max(baseH, reqH);

                // shape.scaleX * shape.width = newW => scaleX = newW / shape.width
                shape.set({
                    scaleX: newW / shape.originalWidth,
                    scaleY: newH / shape.originalHeight
                });"""

new_text_changed = """                let newW = Math.max(baseW, reqW);
                let newH = Math.max(baseH, reqH);

                if (shape.type === 'polygon' && shape.points && shape.points.length === 4) {
                    const ratio = (this.width / newW) + (this.height / newH);
                    if (ratio > 0.85) {
                        const f = ratio / 0.85; newW *= f; newH *= f;
                    }
                } else if (shape.type === 'ellipse') {
                    const ratioSq = Math.pow(this.width / newW, 2) + Math.pow(this.height / newH, 2);
                    if (ratioSq > 0.8) {
                        const f = Math.sqrt(ratioSq / 0.8); newW *= f; newH *= f;
                    }
                }

                shape.set({
                    scaleX: newW / shape.originalWidth,
                    scaleY: newH / shape.originalHeight
                });"""
content = content.replace(old_text_changed, new_text_changed)

# We must also trigger text editing automatically on first click
old_trigger = """            canvas.setActiveObject(textObj);
            
            document.getElementById('sub_toolbar').style.display = 'block';
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel_text').classList.add('active');

            textObj.enterEditing();
            textObj.selectAll();"""

new_trigger = """            textObj.evented = true;
            textObj.selectable = true;
            canvas.setActiveObject(textObj);
            
            document.getElementById('sub_toolbar').style.display = 'block';
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel_text').classList.add('active');

            textObj.enterEditing();
            textObj.selectAll();"""
content = content.replace(old_trigger, new_trigger)

# 3. Handle object:scaling
old_scaling = """                if (currentW < minW) newScaleX = minW / obj.width;
                if (currentH < minH) newScaleY = minH / obj.height;
                
                obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                textObj.set({ width: Math.max(minW, (obj.width * obj.scaleX) - 20) });"""

new_scaling = """                if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                    const tw = textObj.getScaledWidth();
                    const th = textObj.getScaledHeight();
                    const ratio = (tw / currentW) + (th / currentH);
                    if (ratio > 0.85) {
                        const f = ratio / 0.85; newScaleX *= f; newScaleY *= f;
                    }
                } else if (obj.type === 'ellipse') {
                    const tw = textObj.getScaledWidth();
                    const th = textObj.getScaledHeight();
                    const ratioSq = Math.pow(tw / currentW, 2) + Math.pow(th / currentH, 2);
                    if (ratioSq > 0.8) {
                        const f = Math.sqrt(ratioSq / 0.8); newScaleX *= f; newScaleY *= f;
                    }
                } else {
                    if (currentW < minW) newScaleX = minW / obj.width;
                    if (currentH < minH) newScaleY = minH / obj.height;
                }
                
                obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                // Do not auto-expand width of text when scaling shape, keep it proportional or let the user wrap
                textObj.set({ width: Math.max(textObj.width, (obj.width * newScaleX) / (obj.type==='polygon'?1.5:1.2)) });"""
content = content.replace(old_scaling, new_scaling)

# 4. Handle canvas mouse:down for clicking shape to edit text
old_mousedown = """        canvas.on('mouse:down', function(e) {
            const target = e.target;"""
new_mousedown = """        canvas.on('mouse:down', function(e) {
            const target = e.target;
            if (target && target.linkedText && canvas.getActiveObject() === target) {
                const ptr = canvas.getPointer(e.e);
                const t = target.linkedText;
                const w = t.getScaledWidth();
                const h = t.getScaledHeight();
                if (Math.abs(ptr.x - t.left) <= w/2 && Math.abs(ptr.y - t.top) <= h/2) {
                    t.evented = true;
                    t.selectable = true;
                    canvas.setActiveObject(t);
                    
                    document.getElementById('sub_toolbar').style.display = 'block';
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    document.getElementById('panel_text').classList.add('active');
                    
                    t.enterEditing();
                    return;
                }
            }"""
content = content.replace(old_mousedown, new_mousedown)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(content)

print("Patch 5 applied!")
