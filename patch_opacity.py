import sys

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = '''            <span style="margin-left:8px;">색상:</span><div id="btn_text_color" class="color-btn" style="background-color: #E03C31;"></div>
            <span>배경:</span><div id="btn_text_bg" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
        </div>'''
repl1 = '''            <span style="margin-left:8px;">색상:</span><div id="btn_text_color" class="color-btn" style="background-color: #E03C31;"></div>
            <span>배경:</span><div id="btn_text_bg" class="color-btn" style="background-color: transparent; background-image: linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc), linear-gradient(45deg, #ccc 25%, transparent 25%, transparent 75%, #ccc 75%, #ccc); background-size: 10px 10px;"></div>
            <span style="margin-left:8px;">투명도:</span><input type="number" id="text_bg_opacity_input" value="50" min="0" max="100" style="width: 40px; padding: 4px;">
        </div>'''

target2 = '''            if(document.getElementById('text_size_input') && document.getElementById('set_txt_size')) {
                document.getElementById('text_size_input').value = document.getElementById('set_txt_size').value;
            }'''
repl2 = '''            if(document.getElementById('text_size_input') && document.getElementById('set_txt_size')) {
                document.getElementById('text_size_input').value = document.getElementById('set_txt_size').value;
            }
            if(document.getElementById('text_bg_opacity_input') && document.getElementById('set_txt_bg_opacity')) {
                document.getElementById('text_bg_opacity_input').value = document.getElementById('set_txt_bg_opacity').value;
            }'''

target3 = '''        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
            sizeInput.addEventListener('change', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
        }'''
repl3 = '''        const sizeInput = document.getElementById('text_size_input');
        if (sizeInput) {
            sizeInput.addEventListener('input', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
            sizeInput.addEventListener('change', function() { updateActiveText('fontSize', parseInt(this.value) || 50); });
        }
        const bgOpacityInput = document.getElementById('text_bg_opacity_input');
        if (bgOpacityInput) {
            bgOpacityInput.addEventListener('input', function() { 
                const val = parseInt(this.value) || 50;
                if(document.getElementById('set_txt_bg_opacity')) {
                    document.getElementById('set_txt_bg_opacity').value = val;
                }
                updateActiveText('backgroundColor', getTextBgOpacity());
            });
            bgOpacityInput.addEventListener('change', function() { 
                const val = parseInt(this.value) || 50;
                if(document.getElementById('set_txt_bg_opacity')) {
                    document.getElementById('set_txt_bg_opacity').value = val;
                }
                updateActiveText('backgroundColor', getTextBgOpacity());
            });
        }'''

if target1 not in content:
    print('Failed to find Target 1')
elif target2 not in content:
    print('Failed to find Target 2')
elif target3 not in content:
    print('Failed to find Target 3')
else:
    content = content.replace(target1, repl1)
    content = content.replace(target2, repl2)
    content = content.replace(target3, repl3)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully replaced all targets.')
