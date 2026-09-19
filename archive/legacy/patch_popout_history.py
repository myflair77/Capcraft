import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update toObject
old_toObject = r"return originalToObject\.call\(this, \['id', 'linkedTextId', 'linkedShapeId', 'isLinkedText', 'isPlaceholder', 'originalFill', 'originalWidth', 'originalHeight', 'originalScaleX', 'originalScaleY', '_initHeight', 'isArrowBody', 'isArrowHead', 'isEmoji', 'isMosaic', 'strokeDashArray', 'isMediaImage', 'arrowType', 'arrowSize'\]\.concat\(additionalProperties \|\| \[\]\)\);"
new_toObject = r"return originalToObject.call(this, ['id', 'linkedTextId', 'linkedShapeId', 'isLinkedText', 'isPlaceholder', 'originalFill', 'originalWidth', 'originalHeight', 'originalScaleX', 'originalScaleY', '_initHeight', 'isArrowBody', 'isArrowHead', 'isEmoji', 'isMosaic', 'strokeDashArray', 'isMediaImage', 'arrowType', 'arrowSize', 'isPopout', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'tiltX', 'tiltY', 'showConnectionLine', 'linkedOriginalId', 'linkedLineId', '_croppedBgDataUrl'].concat(additionalProperties || []));"
content = re.sub(old_toObject, new_toObject, content)

# 2. Update createPopoutFromObject (add ID generation and dataURL backup)
old_create = r"window\.createPopoutFromObject = function\(obj\) \{"
new_create = r"""window.createPopoutFromObject = function(obj) {
    if (!obj.id) obj.id = 'shape_' + Date.now() + '_' + Math.floor(Math.random() * 1000);"""
content = content.replace(old_create, new_create)

old_linked = r"linkedOriginal: obj,"
new_linked = r"""linkedOriginal: obj,
            linkedOriginalId: obj.id,"""
content = content.replace(old_linked, new_linked)

old_line = r"""        const line = new fabric.Line\(\[0,0,0,0\], \{
            stroke: img.popoutLineColor,"""
new_line = r"""        const line = new fabric.Line([0,0,0,0], {
            id: 'line_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
            stroke: img.popoutLineColor,"""
content = re.sub(old_line, new_line, content)

old_apply = r"""img._croppedBg = croppedBgCanvas;
        applyPopoutTilt\(img\); // Bake the first image with correct tilt & shadows"""
new_apply = r"""img._croppedBg = croppedBgCanvas;
        img._croppedBgDataUrl = croppedBgCanvas.toDataURL(); // 직렬화용 백업
        applyPopoutTilt(img); // Bake the first image with correct tilt & shadows"""
content = re.sub(old_apply, new_apply, content)

old_add_line = r"img\.linkedLine = line;\n\s*canvas\.add\(line\);"
new_add_line = r"""img.linkedLine = line;
        img.linkedLineId = line.id;
        canvas.add(line);"""
content = re.sub(old_add_line, new_add_line, content)

# 3. Inject Restore Logic into finalizeLoad
old_finalize = r"function finalizeLoad\(\) \{"
new_finalize = r"""function finalizeLoad() {
            // Restore Popouts
            const objects = canvas.getObjects();
            objects.forEach(obj => {
                if (obj.isPopout) {
                    if (obj.linkedOriginalId) {
                        obj.linkedOriginal = objects.find(o => o.id === obj.linkedOriginalId);
                    }
                    if (obj.linkedLineId) {
                        obj.linkedLine = objects.find(o => o.id === obj.linkedLineId);
                        if (obj.linkedLine) obj.linkedLine.linkedPopout = obj;
                    }
                    if (obj._croppedBgDataUrl && !obj._croppedBg) {
                        const imgEl = new Image();
                        imgEl.onload = function() {
                            const tCanvas = document.createElement('canvas');
                            tCanvas.width = imgEl.width;
                            tCanvas.height = imgEl.height;
                            tCanvas.getContext('2d').drawImage(imgEl, 0, 0);
                            obj._croppedBg = tCanvas;
                            // Regenerate 3D rendering
                            if (typeof applyPopoutTilt === 'function') {
                                applyPopoutTilt(obj);
                                canvas.requestRenderAll();
                            }
                        };
                        imgEl.src = obj._croppedBgDataUrl;
                    }
                }
            });"""
content = content.replace(old_finalize, new_finalize)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch popout history tracking completed successfully.")
