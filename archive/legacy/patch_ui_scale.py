import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # --- 1. Fix object:scaling ---
    # We want to insert originalScaleX updates at the beginning of the handler
    old_scaling = """        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {"""
            
    new_scaling = """        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                // Update original scales so that textObj's 'changed' event respects the manual resize
                obj.originalScaleX = obj.scaleX;
                obj.originalScaleY = obj.scaleY;
                obj.originalWidth = obj.width;
                obj.originalHeight = obj.height;"""
                
    if old_scaling in content:
        content = content.replace(old_scaling, new_scaling)
    else:
        print("old_scaling not found")

    # --- 2. Fix updateActiveText ---
    old_update = """        function updateActiveText(skipSelection = false) {
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

    new_update = """        function updateActiveText(skipSelection = false) {
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
        
    if old_update in content:
        content = content.replace(old_update, new_update)
    else:
        print("old_update not found")

    # --- 3. Fix btn_txt_* event listeners ---
    old_btn = """        ['b','i','u'].forEach(type => { 
            const topBtn = document.getElementById('btn_txt_'+type);
            const editBtn = document.getElementById('edit_btn_'+type);
            if (topBtn) {
                topBtn.addEventListener('mousedown', e => e.preventDefault());
                topBtn.addEventListener('click', function() { 
                    window['txt'+type.toUpperCase()] = !window['txt'+type.toUpperCase()]; 
                    this.classList.toggle('active'); 
                    updateActiveText(); 
                }); 
            }
            if (editBtn) {
                editBtn.addEventListener('mousedown', e => e.preventDefault());
                editBtn.addEventListener('click', function() { 
                    this.classList.toggle('active'); 
                }); 
            }
        });"""

    new_btn = """        ['b','i','u'].forEach(type => { 
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

    if old_btn in content:
        content = content.replace(old_btn, new_btn)
    else:
        print("old_btn not found")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched index.html")

if __name__ == '__main__':
    main()
