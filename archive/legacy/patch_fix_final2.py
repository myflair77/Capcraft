import io
import re

content = io.open('index.html', 'r', encoding='utf-8').read()

# 1. Fix syncShapeToText
old_sync = """        function syncShapeToText(shape) {
            if (!shape || !shape.linkedText) return;
            const textObj = shape.linkedText;
            const padding = 20;
            const minW = textObj.dynamicMinWidth || 50;
            
            // Sync text width to shape width
            textObj.set({ width: Math.max(minW, (shape.width * shape.scaleX) - padding) });
            
            // Calculate required height based on new text width
            const reqH = textObj.calcTextHeight() + padding;
            
            // Clamp shape height if it's too small
            let baseH = shape.originalHeight * shape.scaleY;
            if (shape.type === 'ellipse') reqH = reqH / Math.sin(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) reqH = reqH / 0.5;
            
            if (baseH < reqH) {
                shape.set({ scaleY: reqH / shape.originalHeight });
            }
            
            // Sync text position and angle
            const center = shape.getCenterPoint();
            textObj.set({ left: center.x, top: center.y, angle: shape.angle });
            textObj.setCoords();
            shape.setCoords();
        }

        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                // Constrain min width manually before syncing
                const minW = obj.linkedText.dynamicMinWidth || 50;
                if ((obj.width * obj.scaleX) < minW + 20) {
                    obj.set('scaleX', (minW + 20) / obj.width);
                }
                
                obj.originalScaleX = obj.scaleX;
                obj.originalScaleY = obj.scaleY;
                obj.originalWidth = obj.width;
                obj.originalHeight = obj.height;
                
                syncShapeToText(obj);
            }
        });"""

new_sync = """        function syncShapeToText(shape, transform) {
            if (!shape || !shape.linkedText) return;
            const textObj = shape.linkedText;
            const padding = 20;
            const minW = textObj.dynamicMinWidth || 50;
            
            // Sync text width to shape width
            textObj.set({ width: Math.max(minW, (shape.width * shape.scaleX) - padding) });
            
            // Calculate required height based on new text width
            let reqH = textObj.calcTextHeight() + padding;
            
            // Clamp shape height if it's too small
            let baseH = shape.originalHeight * shape.scaleY;
            if (shape.type === 'ellipse') reqH = reqH / Math.sin(Math.PI / 4);
            else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) reqH = reqH / 0.5;
            
            let clamped = false;
            let newScaleX = shape.scaleX;
            let newScaleY = shape.scaleY;

            if ((shape.width * shape.scaleX) < minW + 20) {
                newScaleX = (minW + 20) / shape.width;
                clamped = true;
            }
            if (baseH < reqH) {
                newScaleY = reqH / shape.originalHeight;
                clamped = true;
            }
            
            if (clamped) {
                shape.set({ scaleX: newScaleX, scaleY: newScaleY });
                if (transform) {
                    const fixedPoint = shape.getPointByOrigin(transform.originX, transform.originY);
                    shape.setPositionByOrigin(fixedPoint, transform.originX, transform.originY);
                }
            }
            
            // Sync text position and angle
            const center = shape.getCenterPoint();
            textObj.set({ left: center.x, top: center.y, angle: shape.angle });
            textObj.setCoords();
            shape.setCoords();
        }

        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                obj.originalScaleX = obj.scaleX;
                obj.originalScaleY = obj.scaleY;
                obj.originalWidth = obj.width;
                obj.originalHeight = obj.height;
                
                syncShapeToText(obj, e.transform);
            }
        });"""

content = content.replace(old_sync, new_sync)

# 2. Fix palette finalColor error
old_palette = """                paletteEl.style.display = 'none'; 
                if (['text', 'set_text', 'edit_text_c'].includes(targetColorBtn)) {
                    updateActiveText('fill', finalColor);
                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                }"""

new_palette = """                paletteEl.style.display = 'none'; 
                if (['text', 'set_text', 'edit_text_c'].includes(targetColorBtn)) {
                    updateActiveText('fill', c.h);
                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                }"""
content = content.replace(old_palette, new_palette)


# 3. Fix textAlign logic in updateActiveText
old_update = """                if (propName) {
                    if (!skipSelection && hasSelection) {
                        const styleObj = {}; styleObj[propName] = propValue;
                        targetText.setSelectionStyles(styleObj);
                    } else {
                        targetText.set(propName, propValue);
                    }
                }"""

new_update = """                if (propName) {
                    if (!skipSelection && hasSelection && propName !== 'textAlign' && propName !== 'backgroundColor') {
                        const styleObj = {}; styleObj[propName] = propValue;
                        targetText.setSelectionStyles(styleObj);
                    } else {
                        targetText.set(propName, propValue);
                    }
                }"""
content = content.replace(old_update, new_update)

# 4. Fix changed event to use syncShapeToText
old_changed = """            textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                const padding = 20;
                let reqH = this.height + padding;
                let baseH = shape.originalHeight * shape.originalScaleY;

                if (shape.type === 'ellipse') {
                    reqH = reqH / Math.sin(Math.PI / 4);
                } else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) {
                    reqH = reqH / 0.5;
                }

                let newH = Math.max(baseH, reqH);

                shape.set({
                    scaleY: newH / shape.originalHeight
                });
                
                shape.setCoords();
                if (shape.canvas) {
                    shape.canvas.requestRenderAll();
                }
            });"""

new_changed = """            textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                // Just use syncShapeToText but don't clamp width, only height
                const padding = 20;
                let reqH = this.height + padding;
                let baseH = shape.originalHeight * shape.scaleY;

                if (shape.type === 'ellipse') {
                    reqH = reqH / Math.sin(Math.PI / 4);
                } else if (shape.type === 'polygon' && shape.points && shape.points.length === 4) {
                    reqH = reqH / 0.5;
                }

                if (baseH < reqH) {
                    shape.set({ scaleY: reqH / shape.originalHeight });
                    
                    const center = shape.getCenterPoint();
                    this.set({ left: center.x, top: center.y });
                    this.setCoords();
                    shape.setCoords();
                    if (shape.canvas) {
                        shape.canvas.requestRenderAll();
                    }
                }
            });"""

content = content.replace(old_changed, new_changed)

io.open('index.html', 'w', encoding='utf-8').write(content)
print('Applied patches successfully')
