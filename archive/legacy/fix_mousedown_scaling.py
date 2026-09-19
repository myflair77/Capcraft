import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # --- 1. Fix mouse:down logic ---
    old_mousedown = """        canvas.on('mouse:down', o => {
            if (document.getElementById('emoji_popup').style.display === 'block') { document.getElementById('emoji_popup').style.display = 'none'; return; }
            const pointer = canvas.getPointer(o.e);
            lastMouseDownPoint = pointer;
            
            // 붙여넣기 좌표 갱신
            lastCanvasClick = { x: pointer.x, y: pointer.y };

            // 텍스트가 이미 편집 중인 상태라면 Fabric.js 내장 로직(드래그 블록지정, 커서 이동 등)에 위임
            if (o.target && (o.target.isEditing || (o.target.type === 'textbox' && o.target.isEditing))) {
                canvas._currentTransform = null; // 드래그 시 도형 이동(4방향 커서) 방지
                return;
            }"""

    new_mousedown = """        canvas.on('mouse:down', o => {
            if (document.getElementById('emoji_popup').style.display === 'block') { document.getElementById('emoji_popup').style.display = 'none'; return; }
            const pointer = canvas.getPointer(o.e);
            lastMouseDownPoint = pointer;
            
            // 붙여넣기 좌표 갱신
            lastCanvasClick = { x: pointer.x, y: pointer.y };

            // === 텍스트 편집 모드 보호 및 드래그 선택 강화 ===
            if (!activeTool && o.target) {
                let editingText = null;
                if (o.target.isEditing) editingText = o.target;
                else if (o.target.linkedText && o.target.linkedText.isEditing) editingText = o.target.linkedText;
                
                if (editingText) {
                    canvas._currentTransform = null; // 이동 방지 (4방향 커서 방지)
                    if (canvas.getActiveObject() !== editingText) {
                        canvas.setActiveObject(editingText);
                    }
                    if (o.target !== editingText) {
                        // 도형의 빈 공간을 클릭한 경우, 텍스트 객체에 직접 마우스 이벤트를 전달한 효과를 줌
                        if (typeof editingText.setCursorByClick === 'function') {
                            try { editingText.setCursorByClick(o.e); } catch(e) {}
                        }
                        if (typeof editingText.initMouseMoveHandler === 'function') {
                            try { editingText.initMouseMoveHandler(o.e); } catch(e) {}
                        }
                    }
                    return;
                }
            }"""

    if old_mousedown in content:
        content = content.replace(old_mousedown, new_mousedown)
    else:
        print("old_mousedown not found")

    # --- 2. Revert object:scaling to exact original ---
    
    # We will find the object:scaling block and replace it
    start_idx = content.find("        canvas.on('object:scaling',")
    end_idx = content.find("        canvas.on('object:rotating',", start_idx)
    
    if start_idx != -1 and end_idx != -1:
        orig_scaling = """        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const textObj = obj.linkedText;
                const minW = textObj.dynamicMinWidth || 50;
                const minH = textObj.calcTextHeight() + 20;
                const currentW = obj.width * obj.scaleX;
                const currentH = obj.height * obj.scaleY;
                
                let newScaleX = obj.scaleX;
                let newScaleY = obj.scaleY;
                let clamped = false;
                
                const minScaleX = minW / obj.width;
                const minScaleY = minH / obj.height;
                
                const isCorner = e.transform && ['tl', 'tr', 'bl', 'br'].includes(e.transform.corner);
                
                if (isCorner) {
                    if (currentW < minW || currentH < minH) {
                        let requiredRatioX = minScaleX / newScaleX;
                        let requiredRatioY = minScaleY / newScaleY;
                        let maxRatio = Math.max(requiredRatioX, requiredRatioY);
                        if (maxRatio > 1) {
                            newScaleX *= maxRatio;
                            newScaleY *= maxRatio;
                            clamped = true;
                        }
                    }
                } else {
                    if (currentW < minW) { newScaleX = minScaleX; clamped = true; }
                    if (currentH < minH) { newScaleY = minScaleY; clamped = true; }
                }
                
                if (clamped && e.transform) {
                    const originX = e.transform.originX;
                    const originY = e.transform.originY;
                    const fixedPoint = obj.getPointByOrigin(originX, originY);
                    
                    obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                    obj.setPositionByOrigin(fixedPoint, originX, originY);
                }
                
                const center = obj.getCenterPoint();
                textObj.set({ 
                    width: Math.max(minW, (obj.width * obj.scaleX) - 20),
                    left: center.x,
                    top: center.y,
                    angle: obj.angle
                });
                textObj.setCoords();
            }
        });

"""
        content = content[:start_idx] + orig_scaling + content[end_idx:]
    else:
        print("object:scaling block not found")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed mouse:down and object:scaling")

if __name__ == '__main__':
    main()
