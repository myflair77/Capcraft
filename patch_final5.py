import io

content = io.open('index.html', 'r', encoding='utf-8').read()

# 1. syncShapeToText
start_idx = content.find("function syncShapeToText(shape, transform) {")
end_idx = content.find("        }", start_idx) + 9
old_sync = content[start_idx:end_idx]

new_sync = """function syncShapeToText(shape, transform) {
            if (!shape || !shape.linkedText) return;
            const textObj = shape.linkedText;
            const padding = 20;
            const minW = textObj.dynamicMinWidth || 50;
            
            let maxTextW = shape.width * shape.scaleX;
            if (shape.type === 'ellipse') maxTextW *= Math.cos(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) maxTextW *= 0.5;

            let clampedX = false;
            let newScaleX = shape.scaleX;
            
            if (maxTextW < minW + padding) {
                newScaleX = (minW + padding) / (maxTextW / shape.scaleX);
                clampedX = true;
                maxTextW = shape.width * newScaleX;
                if (shape.type === 'ellipse') maxTextW *= Math.cos(Math.PI / 4);
                else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) maxTextW *= 0.5;
            }

            textObj.set({ width: Math.max(minW, maxTextW - padding) });
            
            let reqH = textObj.calcTextHeight() + padding;
            let maxTextH = shape.originalHeight * shape.scaleY;
            
            if (shape.type === 'ellipse') reqH = reqH / Math.cos(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) reqH = reqH / 0.5;

            let clampedY = false;
            let newScaleY = shape.scaleY;

            if (maxTextH < reqH) {
                newScaleY = reqH / shape.originalHeight;
                clampedY = true;
            }

            if (clampedX || clampedY) {
                let dx = shape.width * (newScaleX - shape.scaleX);
                let dy = shape.height * (newScaleY - shape.scaleY);
                
                shape.scaleX = newScaleX;
                shape.scaleY = newScaleY;

                if (transform) {
                    let rad = shape.angle * Math.PI / 180;
                    let localDx = 0; let localDy = 0;
                    if (transform.originX === 'left') localDx = dx / 2;
                    else if (transform.originX === 'right') localDx = -dx / 2;
                    if (transform.originY === 'top') localDy = dy / 2;
                    else if (transform.originY === 'bottom') localDy = -dy / 2;

                    shape.left += localDx * Math.cos(rad) - localDy * Math.sin(rad);
                    shape.top += localDx * Math.sin(rad) + localDy * Math.cos(rad);
                }
            }
            
            const center = shape.getCenterPoint();
            textObj.set({ left: center.x, top: center.y, angle: shape.angle });
            textObj.setCoords();
        }"""
content = content.replace(old_sync, new_sync)

# 2. Add isWidthFixed
content = content.replace("splitByGrapheme: true,\n                hoverCursor: 'move'", "splitByGrapheme: true,\n                isWidthFixed: true,\n                hoverCursor: 'move'")

# 3. textObj.on('changed')
start_idx = content.find("textObj.on('changed', function() {")
end_idx = content.find("            });\n\n            obj.setControlVisible('addText', false);", start_idx) + 15
old_changed = content[start_idx:end_idx]

new_changed = """textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                const padding = 20;
                let maxTextW = shape.width * shape.scaleX;
                if (shape.type === 'ellipse') maxTextW *= Math.cos(Math.PI / 4);
                else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) maxTextW *= 0.5;
                
                this.set({ width: Math.max(50, maxTextW - padding) });
                
                let reqH = this.calcTextHeight() + padding;
                if (shape.type === 'ellipse') reqH = reqH / Math.cos(Math.PI / 4);
                else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) reqH = reqH / 0.5;

                let targetScaleY = Math.max(shape.originalScaleY || 1, reqH / shape.originalHeight);
                shape.set({ scaleY: targetScaleY });
                
                const center = shape.getCenterPoint();
                this.set({ left: center.x, top: center.y });
                this.setCoords();
                shape.setCoords();
                if (shape.canvas) {
                    shape.canvas.requestRenderAll();
                }
            });"""
content = content.replace(old_changed, new_changed)

# 4. Color picker mousedown
content = content.replace("cell.addEventListener('click', () => {", "cell.addEventListener('mousedown', e => e.preventDefault());\n            cell.addEventListener('click', () => {")

# 5. Color buttons mousedown
content = content.replace("bindCP('btn_text_color', 'text'); bindCP('btn_text_bg', 'text_bg');", "document.getElementById('btn_text_color').addEventListener('mousedown', e => e.preventDefault());\n        document.getElementById('btn_text_bg').addEventListener('mousedown', e => e.preventDefault());\n        bindCP('btn_text_color', 'text'); bindCP('btn_text_bg', 'text_bg');")

# 6. updateActiveText
start_idx = content.find("function updateActiveText(propName = null, propValue = null, skipSelection = false) {")
end_idx = content.find("            }\n        }\n        ['b','i','u'].forEach(type => {", start_idx) + 13
old_update_text = content[start_idx:end_idx]

new_update_text = """function updateActiveText(propName = null, propValue = null, skipSelection = false) {
            if (propName && typeof propName === 'object') { propName = null; propValue = null; }
            const obj = canvas.getActiveObject();
            if (!obj) return;
            const targetText = obj.linkedText || (['i-text', 'textbox', 'text'].includes(obj.type) && !obj.isEmoji ? obj : null);
            if (targetText) {
                const hasSelection = targetText.isEditing && targetText.selectionStart !== targetText.selectionEnd;

                if (propName) {
                    if (!skipSelection && hasSelection && propName !== 'textAlign' && propName !== 'backgroundColor') {
                        const styleObj = {}; styleObj[propName] = propValue;
                        targetText.setSelectionStyles(styleObj);
                    } else {
                        targetText.set(propName, propValue);
                    }
                } else {
                    const isB = document.getElementById('btn_txt_b') && document.getElementById('btn_txt_b').classList.contains('active');
                    const isI = document.getElementById('btn_txt_i') && document.getElementById('btn_txt_i').classList.contains('active');
                    const isU = document.getElementById('btn_txt_u') && document.getElementById('btn_txt_u').classList.contains('active');
                    const fw = isB ? 'bold' : 'normal';
                    const fst = isI ? 'italic' : 'normal';
                    const und = !!isU;
                    const fs = parseInt(document.getElementById('text_size_input').value) || 50;
                    let alignVal = 'center';
                    if (document.getElementById('text_align')) alignVal = document.getElementById('text_align').value;
                    if (document.getElementById('edit_text_align')) alignVal = document.getElementById('edit_text_align').value;

                    if (!skipSelection && hasSelection) {
                        targetText.setSelectionStyles({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor });
                    } else {
                        targetText.set({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor, backgroundColor: getTextBgOpacity(), textAlign: alignVal });
                    }
                }
                targetText.dirty = true;
                if (targetText.isEditing && targetText.initDimensions) {
                    targetText.initDimensions();
                }
                if (targetText.linkedShape) targetText.fire('changed');
                canvas.requestRenderAll();
            }
        }"""
content = content.replace(old_update_text, new_update_text)

io.open('index.html', 'w', encoding='utf-8').write(content)
print("Patch applied.")
