with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update canvas instantiation to support Ctrl and Shift multi-selection
old_canvas_init = """        const canvas = new fabric.Canvas('mainCanvas', {
            uniformScaling: false,
            width: 800, height: 600, selection: true,
            imageSmoothingEnabled: true,
            imageSmoothingQuality: 'high',
            perPixelTargetFind: false,
            targetFindTolerance: 25,
            preserveObjectStacking: true,
            enableRetinaScaling: true
        });"""

new_canvas_init = """        const canvas = new fabric.Canvas('mainCanvas', {
            uniformScaling: false,
            width: 800, height: 600, selection: true,
            imageSmoothingEnabled: true,
            imageSmoothingQuality: 'high',
            perPixelTargetFind: false,
            targetFindTolerance: 25,
            preserveObjectStacking: true,
            enableRetinaScaling: true
        });

        // Ctrl 및 Shift 키를 누른 상태에서의 다중 선택(Multi-selection) 지원
        canvas.selectionKey = ['shiftKey', 'ctrlKey'];
        canvas._isSelectionKeyPressed = function (e) {
            return !!(e && (e.shiftKey || e.ctrlKey || e.metaKey));
        };"""

content = content.replace(old_canvas_init, new_canvas_init)

# 2. Update contextmenu to preserve activeSelection when right clicking on a selected item
old_ctx_menu = """                if (target) {
                    canvas.setActiveObject(target);
                    canvas.requestRenderAll();"""

new_ctx_menu = """                if (target) {
                    const activeObj = canvas.getActiveObject();
                    if (activeObj && activeObj.type === 'activeSelection' && typeof activeObj.contains === 'function' && activeObj.contains(target)) {
                        // 다중 선택 객체 내부의 요소를 우클릭 시 다중 선택 상태(activeSelection) 유지
                    } else {
                        canvas.setActiveObject(target);
                    }
                    canvas.requestRenderAll();"""

content = content.replace(old_ctx_menu, new_ctx_menu)

# 3. Update mouse:down linkedText/linkedShape handler so Ctrl/Shift multi-selection is not overridden
old_mouse_down_linked = """            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집
            const isControl = canvas._currentTransform && canvas._currentTransform.action && canvas._currentTransform.action !== 'drag';
            if (!activeTool && o.target && o.target.linkedShape && !isControl) {"""

new_mouse_down_linked = """            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집 (Ctrl/Shift 다중 선택 시에는 리다이렉트 스킵)
            const isControl = canvas._currentTransform && canvas._currentTransform.action && canvas._currentTransform.action !== 'drag';
            const isMultiKey = o.e && (o.e.ctrlKey || o.e.shiftKey || o.e.metaKey);
            if (!activeTool && o.target && o.target.linkedShape && !isControl && !isMultiKey) {"""

content = content.replace(old_mouse_down_linked, new_mouse_down_linked)

# 4. Enhance Delete / Backspace multi-selection removal
old_del_handler = """            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (activeObj) {
                    canvas.getActiveObjects().forEach(obj => {
                        if (obj.__isLineHandle) return; // 핸들 자체는 삭제하지 않음
                        if (obj.__capcraftHandles) removeLineHandles(obj); // 선분 삭제 시 핸들도 제거
                        canvas.remove(obj);
                    });
                    canvas.discardActiveObject();
                    saveHistory();
                }
            }"""

new_del_handler = """            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (activeObj) {
                    const activeObjs = canvas.getActiveObjects();
                    activeObjs.forEach(obj => {
                        if (obj.__isLineHandle) return; // 핸들 자체는 삭제하지 않음
                        if (obj.__capcraftHandles) removeLineHandles(obj); // 선분 삭제 시 핸들도 제거
                        if (obj.linkedText) canvas.remove(obj.linkedText);
                        if (obj.linkedShape) canvas.remove(obj.linkedShape);
                        if (obj.isPopout && obj.linkedLine) canvas.remove(obj.linkedLine);
                        canvas.remove(obj);
                    });
                    canvas.discardActiveObject();
                    canvas.requestRenderAll();
                    saveHistory();
                }
            }"""

content = content.replace(old_del_handler, new_del_handler)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Multi-selection patch applied to index.html successfully!')
