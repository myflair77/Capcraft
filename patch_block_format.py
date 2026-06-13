import io
content = io.open('index.html', 'r', encoding='utf-8').read()

# 1. Replace updateActiveText
old_update = """        function updateActiveText(skipSelection = false) {
            const obj = canvas.getActiveObject();
            if (!obj) return;
            const targetText = obj.linkedText || (['i-text', 'textbox', 'text'].includes(obj.type) && !obj.isEmoji ? obj : null);
            if (targetText) {
                // UI 버튼 상태에서 직접 값을 읽어옴 (txtB, txtI, txtU 전역 변수 충돌 방지)
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

                if (!skipSelection && targetText.isEditing && targetText.selectionStart !== targetText.selectionEnd) {
                    targetText.setSelectionStyles({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor });
                } else {
                    targetText.set({ fontWeight: fw, fontStyle: fst, underline: und, fontSize: fs, fill: textColor, backgroundColor: getTextBgOpacity(), textAlign: alignVal });
                }
                if (targetText.linkedShape) targetText.fire('changed');
                canvas.requestRenderAll();
            }
        }"""

new_update = """        function updateActiveText(propName = null, propValue = null, skipSelection = false) {
            if (propName && typeof propName === 'object') { propName = null; propValue = null; }
            const obj = canvas.getActiveObject();
            if (!obj) return;
            const targetText = obj.linkedText || (['i-text', 'textbox', 'text'].includes(obj.type) && !obj.isEmoji ? obj : null);
            if (targetText) {
                const hasSelection = targetText.isEditing && targetText.selectionStart !== targetText.selectionEnd;

                if (propName) {
                    if (!skipSelection && hasSelection) {
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
                if (targetText.linkedShape) targetText.fire('changed');
                canvas.requestRenderAll();
            }
        }"""
content = content.replace(old_update, new_update)


# 2. Replace BIU logic
old_biu = """        ['b','i','u'].forEach(type => { 
            const topBtn = document.getElementById('btn_txt_'+type);
            const editBtn = document.getElementById('edit_btn_'+type);
            if (topBtn) {
                topBtn.addEventListener('mousedown', e => e.preventDefault());
                topBtn.addEventListener('click', function() { 
                    this.classList.toggle('active'); 
                    if (editBtn) editBtn.classList.toggle('active', this.classList.contains('active'));
                    updateActiveText(); 
                }); 
            }
            if (editBtn) {
                editBtn.addEventListener('mousedown', e => e.preventDefault());
                editBtn.addEventListener('click', function() { 
                    this.classList.toggle('active'); 
                    if (topBtn) topBtn.classList.toggle('active', this.classList.contains('active'));
                    updateActiveText();
                }); 
            }
        });"""

new_biu = """        ['b','i','u'].forEach(type => { 
            const topBtn = document.getElementById('btn_txt_'+type);
            const editBtn = document.getElementById('edit_btn_'+type);
            function onClick() {
                this.classList.toggle('active'); 
                const isActive = this.classList.contains('active');
                if (editBtn && this === topBtn) editBtn.classList.toggle('active', isActive);
                if (topBtn && this === editBtn) topBtn.classList.toggle('active', isActive);
                
                let pName, pVal;
                if(type === 'b') { pName = 'fontWeight'; pVal = isActive ? 'bold' : 'normal'; }
                if(type === 'i') { pName = 'fontStyle'; pVal = isActive ? 'italic' : 'normal'; }
                if(type === 'u') { pName = 'underline'; pVal = isActive; }
                updateActiveText(pName, pVal);
            }
            if (topBtn) { topBtn.addEventListener('mousedown', e => e.preventDefault()); topBtn.addEventListener('click', onClick); }
            if (editBtn) { editBtn.addEventListener('mousedown', e => e.preventDefault()); editBtn.addEventListener('click', onClick); }
        });"""
content = content.replace(old_biu, new_biu)


# 3. Replace align logic
old_align = """                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        if (document.getElementById('text_align')) document.getElementById('text_align').value = val;
                        updateActiveText();
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            if (document.getElementById('edit_text_align')) document.getElementById('edit_text_align').value = val;
                            updateActiveText();
                        }
                    }"""

new_align = """                    if (group.id === 'edit_text_align_group') {
                        document.getElementById('edit_text_align').value = val;
                        if (document.getElementById('text_align')) document.getElementById('text_align').value = val;
                    } else {
                        // main toolbar align group
                        if (document.getElementById('text_align')) {
                            document.getElementById('text_align').value = val;
                            if (document.getElementById('edit_text_align')) document.getElementById('edit_text_align').value = val;
                        }
                    }
                    updateActiveText('textAlign', val);"""
content = content.replace(old_align, new_align)


# 4. Replace size logic
old_size = """        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', updateActiveText);
            sizeInput.addEventListener('change', updateActiveText);
        }
        const editSizeInput = document.getElementById('edit_text_size');
        if (editSizeInput) {
            editSizeInput.addEventListener('input', function() {
                if(document.getElementById('text_size_input')) {
                    document.getElementById('text_size_input').value = this.value;
                }
                updateActiveText();
            });
        }"""

new_size = """        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
            sizeInput.addEventListener('change', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
        }
        const editSizeInput = document.getElementById('edit_text_size');
        if (editSizeInput) {
            editSizeInput.addEventListener('input', function() {
                const val = parseInt(this.value) || 50;
                if(document.getElementById('text_size_input')) {
                    document.getElementById('text_size_input').value = val;
                }
                updateActiveText('fontSize', val);
            });
        }"""
content = content.replace(old_size, new_size)

# 5. Replace palette logic
old_pal = """                paletteEl.style.display = 'none'; if(activeTool==='text') updateActiveText();"""
new_pal = """                paletteEl.style.display = 'none'; 
                if(activeTool==='text') {
                    if (targetColorBtn === 'text') updateActiveText('fill', textColor);
                    else if (targetColorBtn === 'text_bg') updateActiveText('backgroundColor', getTextBgOpacity());
                    else updateActiveText();
                }"""
content = content.replace(old_pal, new_pal)

io.open('index.html', 'w', encoding='utf-8').write(content)
print("Finished patching index.html for block formatting")
