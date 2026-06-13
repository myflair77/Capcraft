import sys

def patch_file():
    with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 1. '비율유지' -> '비율 유지'
    content = content.replace('비율유지</label>', '비율 유지</label>')
    content = content.replace('가로세로 비율 유지</label>', '비율 유지</label>')

    # 2. Add '배경 투명도' to edit_shape
    shape_fill = '<span style="margin-left:10px;">배경색:</span><div id="edit_shape_fill" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>'
    new_shape_fill = shape_fill + '\n<span style="margin-left:10px;">배경 투명도:</span><input type="number" id="edit_shape_bg_opacity" value="50" min="0" max="100" style="width: 40px; padding: 4px;">'
    content = content.replace(shape_fill, new_shape_fill)

    # 3. Add '배경 투명도' to edit_line
    line_fill = '<span style="margin-left:10px;">배경색:</span><div id="edit_line_fill" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>'
    new_line_fill = line_fill + '\n<span style="margin-left:10px;">배경 투명도:</span><input type="number" id="edit_line_bg_opacity" value="50" min="0" max="100" style="width: 40px; padding: 4px;">'
    content = content.replace(line_fill, new_line_fill)

    # 4. Update isImage definition to include emoji and mosaic for properties window
    # In canvas.on('mouse:dblclick')
    content = content.replace("const isImage = (editingObject.type === 'image' && !editingObject.isMosaic) || editingObject.isMediaImage;", 
                              "const isImage = (editingObject.type === 'image') || editingObject.isMediaImage || editingObject.isEmoji || editingObject.isMosaic;")
    # In window.applyObjectEdit
    content = content.replace("const isImage = (editingObject.type === 'image' && !editingObject.isMosaic) || editingObject.isMediaImage;", 
                              "const isImage = (editingObject.type === 'image') || editingObject.isMediaImage || editingObject.isEmoji || editingObject.isMosaic;")

    # Remove the form_edit_emoji UI and logic to prevent conflicts, since isEmoji is now bundled with isImage
    content = content.replace("document.getElementById('form_edit_emoji').style.display = 'none';", "")

    emoji_logic = '''
                if (isEmoji) {
                    document.getElementById('form_edit_emoji').style.display = 'block';
                    const currentSize = editingObject.baseFontSize ? Math.round(editingObject.baseFontSize * editingObject.scaleX) : (editingObject.fontSize || 36);
                    document.getElementById('edit_emoji_size').value = currentSize;
                }
                else if (isImage) {'''
    content = content.replace(emoji_logic, "if (isImage) {")

    emoji_apply = '''
            if (isEmoji) {
                const size = parseInt(document.getElementById('edit_emoji_size').value);
                if (editingObject.baseFontSize) { // Image로 변환된 텍스트이모티콘
                    const scale = size / editingObject.baseFontSize;
                    editingObject.set({ scaleX: scale, scaleY: scale });
                } else { // 이전 버전 호환성 (fabric.Text로 유지된 경우)
                    editingObject.set({ fontSize: size });
                }
                editingObject.setCoords();
            } else if (isImage) {'''
    content = content.replace(emoji_apply, "if (isImage) {")

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("UI and JS logic updated for edit forms.")

patch_file()
