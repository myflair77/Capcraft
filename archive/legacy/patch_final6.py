import io

content = io.open('index.html', 'r', encoding='utf-8').read()
lines = content.split('\n')

# 1. syncShapeToText
start_sync = -1
end_sync = -1
for i, line in enumerate(lines):
    if 'function syncShapeToText(shape, transform) {' in line:
        start_sync = i
    if start_sync != -1 and i > start_sync and '        }' in line and '// shape.setCoords() removed' in lines[i-1]:
        end_sync = i
        break

new_sync = """        function syncShapeToText(shape, transform) {
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
if start_sync != -1 and end_sync != -1:
    lines = lines[:start_sync] + new_sync.split('\n') + lines[end_sync+1:]

# 2. Add isWidthFixed
for i, line in enumerate(lines):
    if 'splitByGrapheme: true,' in line and 'hoverCursor:' in lines[i+1]:
        lines.insert(i+1, "                isWidthFixed: true,")
        break

# 3. textObj.on('changed')
start_ch = -1
end_ch = -1
for i, line in enumerate(lines):
    if "textObj.on('changed', function() {" in line:
        start_ch = i
    if start_ch != -1 and i > start_ch and '            });' in line and 'obj.setControlVisible' in lines[i+2]:
        end_ch = i
        break

new_changed = """            textObj.on('changed', function() {
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
if start_ch != -1 and end_ch != -1:
    lines = lines[:start_ch] + new_changed.split('\n') + lines[end_ch+1:]

# 4. Color picker mousedown
for i, line in enumerate(lines):
    if "cell.addEventListener('click', () => {" in line and 'bgImg' in lines[i+1]:
        lines.insert(i, "            cell.addEventListener('mousedown', e => e.preventDefault());")
        break

# 5. Color buttons mousedown
for i, line in enumerate(lines):
    if "bindCP('btn_text_color', 'text'); bindCP('btn_text_bg', 'text_bg');" in line:
        lines.insert(i, "        document.getElementById('btn_text_color').addEventListener('mousedown', e => e.preventDefault());")
        lines.insert(i+1, "        document.getElementById('btn_text_bg').addEventListener('mousedown', e => e.preventDefault());")
        break

# 6. updateActiveText
start_up = -1
end_up = -1
for i, line in enumerate(lines):
    if "function updateActiveText(propName = null, propValue = null, skipSelection = false) {" in line:
        start_up = i
    if start_up != -1 and i > start_up and '        }' in line and "['b','i','u'].forEach(type => {" in lines[i+1]:
        end_up = i
        break

new_up = """        function updateActiveText(propName = null, propValue = null, skipSelection = false) {
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
if start_up != -1 and end_up != -1:
    lines = lines[:start_up] + new_up.split('\n') + lines[end_up+1:]

io.open('index.html', 'w', encoding='utf-8').write('\n'.join(lines))
print('Done!')
