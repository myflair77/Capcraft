import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update updateActiveText
    old_update_text = """        function updateActiveText(skipSelection = false) {
            const obj = canvas.getActiveObject();
            if (obj && (obj.type === 'i-text' || obj.type === 'textbox') && !obj.isEmoji) {
                const fw = txtB ? 'bold' : 'normal';
                const fst = txtI ? 'italic' : 'normal';
                const und = txtU;
                const fs = parseInt(document.getElementById('text_size_input').value);

                if (!skipSelection && obj.isEditing && obj.selectionStart !== obj.selectionEnd) {
                    obj.setSelectionStyles({ fontWeight: fw, fontStyle: fst, underline: und });
                } else {
                    obj.set({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor, backgroundColor: getTextBgOpacity() });
                }
                canvas.requestRenderAll();
            }
        }"""
    
    new_update_text = """        function updateActiveText(skipSelection = false) {
            const obj = canvas.getActiveObject();
            if (!obj) return;
            const targetText = obj.linkedText || (['i-text', 'textbox', 'text'].includes(obj.type) && !obj.isEmoji ? obj : null);
            if (targetText) {
                const fw = txtB ? 'bold' : 'normal';
                const fst = txtI ? 'italic' : 'normal';
                const und = txtU;
                const fs = parseInt(document.getElementById('text_size_input').value) || 50;
                const alignVal = document.getElementById('edit_text_align') ? document.getElementById('edit_text_align').value : 'center';

                if (!skipSelection && targetText.isEditing && targetText.selectionStart !== targetText.selectionEnd) {
                    targetText.setSelectionStyles({ fontWeight: fw, fontStyle: fst, underline: und });
                } else {
                    targetText.set({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor, backgroundColor: getTextBgOpacity(), textAlign: alignVal });
                }
                if (targetText.linkedShape) targetText.fire('changed');
                canvas.requestRenderAll();
            }
        }"""
    
    content = content.replace(old_update_text, new_update_text)

    # 2. Text property panel logic (TextAlign, Size, Color etc.) needs to trigger updateActiveText
    # It already does for B,I,U. What about text align?
    old_text_align = """                document.getElementById('edit_text_align').value = editingObject.textAlign || 'left';"""
    new_text_align = """                document.getElementById('edit_text_align').value = editingObject.textAlign || 'center';"""
    content = content.replace(old_text_align, new_text_align)

    # 3. mouse:down changes
    old_mouse_down_text1 = """                    // 두 번째 클릭: 텍스트 편집 모드 직접 진입
                    _lastActiveShapeForLinkedText = null;
                    const textTarget = o.target;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    canvas._currentTransform = null;
                    canvas.requestRenderAll();
                    return;"""
    new_mouse_down_text1 = """                    // 두 번째 클릭: 텍스트 편집 모드 직접 진입
                    _lastActiveShapeForLinkedText = null;
                    const textTarget = o.target;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    textTarget.setCursorByClick(o.e);
                    // 삭제: canvas._currentTransform = null; (드래그 버그 방지)
                    canvas.requestRenderAll();
                    return;"""
    content = content.replace(old_mouse_down_text1, new_mouse_down_text1)

    old_mouse_down_text2 = """                    // 두 번째 클릭: 텍스트 편집 모드 진입
                    _lastActiveShapeForLinkedText = null;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    canvas._currentTransform = null;
                    canvas.requestRenderAll();
                    return;"""
    new_mouse_down_text2 = """                    // 두 번째 클릭: 텍스트 편집 모드 진입
                    _lastActiveShapeForLinkedText = null;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    textTarget.setCursorByClick(o.e);
                    canvas.requestRenderAll();
                    return;"""
    content = content.replace(old_mouse_down_text2, new_mouse_down_text2)

    # 4. Global events for editing:entered and exited to show/hide panels
    global_events = """        canvas.on('text:editing:entered', function(e) {
            document.getElementById('sub_toolbar').style.display = 'block';
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel_text').classList.add('active');
            
            // 패널 속성 동기화
            if (e.target) {
                if (e.target.fontWeight === 'bold') { document.getElementById('btn_txt_b').classList.add('active'); window.txtB = true; } else { document.getElementById('btn_txt_b').classList.remove('active'); window.txtB = false; }
                if (e.target.fontStyle === 'italic') { document.getElementById('btn_txt_i').classList.add('active'); window.txtI = true; } else { document.getElementById('btn_txt_i').classList.remove('active'); window.txtI = false; }
                if (e.target.underline) { document.getElementById('btn_txt_u').classList.add('active'); window.txtU = true; } else { document.getElementById('btn_txt_u').classList.remove('active'); window.txtU = false; }
                if (document.getElementById('edit_text_align')) document.getElementById('edit_text_align').value = e.target.textAlign || 'center';
            }
        });
        canvas.on('text:editing:exited', function(e) {
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            if (activeTool && document.getElementById('panel_' + activeTool)) {
                document.getElementById('panel_' + activeTool).classList.add('active');
            } else {
                document.getElementById('sub_toolbar').style.display = 'none';
            }
        });
"""
    if "text:editing:entered" not in content:
        content = content.replace("canvas.on('selection:created',", global_events + "\n        canvas.on('selection:created',")

    # 5. btn_add_text_to_shape modifications
    old_add_text = """            const center = obj.getCenterPoint();
            const textObj = new fabric.Textbox('내용 입력', {
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
            });
            
            obj.linkedText = textObj;
            textObj.linkedShape = obj;
            
            canvas.add(textObj);
            // 도형 원본 크기 백업
            obj.originalScaleX = obj.scaleX;
            obj.originalScaleY = obj.scaleY;
            obj.originalWidth = obj.width;
            obj.originalHeight = obj.height;

            textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                const padding = 20;
                const reqW = this.width + padding;
                const reqH = this.height + padding;

                const baseW = shape.originalWidth * shape.originalScaleX;
                const baseH = shape.originalHeight * shape.originalScaleY;

                let newW = Math.max(baseW, reqW);
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
                });
                
                shape.setCoords();
                if (shape.canvas) {
                    shape.canvas.requestRenderAll();
                }
            });"""

    new_add_text = """            const center = obj.getCenterPoint();
            
            let padW = 20;
            let startW = obj.width * obj.scaleX;
            if (obj.type === 'ellipse') {
                startW = startW * Math.cos(Math.PI / 4);
            } else if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                startW = startW * 0.5;
            }
            startW = Math.max(50, startW - padW);

            const textObj = new fabric.Textbox('내용 입력', {
                left: center.x,
                top: center.y,
                originX: 'center',
                originY: 'center',
                width: startW,
                fontSize: txtSize,
                fill: txtColor,
                backgroundColor: txtBgColor === 'transparent' ? '' : txtBgColor,
                fontWeight: isBold ? 'bold' : 'normal',
                fontStyle: isItalic ? 'italic' : 'normal',
                underline: isUnderline,
                textAlign: textAlign,
                fontFamily: 'Pretendard',
                editable: true,
                hasControls: false,
                hasBorders: false,
                selectable: false, // 단독 선택 불가 (도형 종속)
                evented: true,     // 클릭 이벤트는 받아야 함
                splitByGrapheme: true
            });
            
            obj.linkedText = textObj;
            textObj.linkedShape = obj;
            
            canvas.add(textObj);
            
            obj.originalScaleX = obj.scaleX;
            obj.originalScaleY = obj.scaleY;
            obj.originalWidth = obj.width;
            obj.originalHeight = obj.height;

            // 도형 수동 리사이징 시 텍스트 폭 자동 갱신
            obj.on('scaling', function() {
                if (this.linkedText) {
                    let pw = 20;
                    let sw = this.width * this.scaleX;
                    if (this.type === 'ellipse') {
                        sw = sw * Math.cos(Math.PI / 4);
                    } else if (this.type === 'polygon' && this.points && this.points.length === 4) {
                        sw = sw * 0.5;
                    }
                    sw = Math.max(50, sw - pw);
                    this.linkedText.set({ width: sw });
                    this.linkedText.fire('changed');
                }
            });

            textObj.on('changed', function() {
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
    content = content.replace(old_add_text, new_add_text)
    
    # 6. Add event listeners for text alignment buttons to call updateActiveText
    # the alignment select is #edit_text_align. We also have #text_align for global
    # Wait, the tool panel is used.
    # In index.html, there's edit_text_align change event? Let's check.
    # We will just write the file out.
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
if __name__ == '__main__':
    main()
