import io
content = io.open('index.html', 'r', encoding='utf-8').read()

old_moving_sync = """            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
            }"""

new_moving_sync = """            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
                canvas.requestRenderAll();
            }"""

if old_moving_sync in content:
    content = content.replace(old_moving_sync, new_moving_sync)
    print("patched moving sync")
else:
    print("old_moving_sync not found")

old_palette = """                paletteEl.style.display = 'none'; 
                if(activeTool==='text') {
                    if (targetColorBtn === 'text') updateActiveText('fill', textColor);
                    else if (targetColorBtn === 'text_bg') updateActiveText('backgroundColor', getTextBgOpacity());
                    else updateActiveText();
                }"""

new_palette = """                paletteEl.style.display = 'none'; 
                if (['text', 'set_text', 'edit_text_c'].includes(targetColorBtn)) {
                    updateActiveText('fill', finalColor);
                } else if (['text_bg', 'set_text_bg', 'edit_text_b'].includes(targetColorBtn)) {
                    updateActiveText('backgroundColor', getTextBgOpacity());
                }"""

if old_palette in content:
    content = content.replace(old_palette, new_palette)
    print("patched palette sync")
else:
    print("old_palette not found")

io.open('index.html', 'w', encoding='utf-8').write(content)
