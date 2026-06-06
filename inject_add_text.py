import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject hidden HTML button for test.js compatibility and logic handling
html_btn = '<button id="btn_add_text_to_shape" style="display:none;"></button>\n            <button class="btn-tool disabled" id="btn_action_copy">'
content = content.replace('<button class="btn-tool disabled" id="btn_action_copy">', html_btn)

# 2. Inject addText fabric.Control definition next to flipY
add_text_control_code = """
            const addTextIcon = "data:image/svg+xml;utf8," + encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='4' fill='white' stroke='#3b82f6' stroke-width='2'/><path d='M7 7h10v2h-4v8h-2v-8H7V7z' fill='#3b82f6'/></svg>");
            const addTextImg = new Image(); addTextImg.src = addTextIcon;

            controls.addText = new fabric.Control({
                x: 0, y: -0.5, offsetY: -40, offsetX: -125, cursorStyle: 'pointer',
                mouseDownHandler: function(eventData, transform, x, y) {
                    const target = transform.target;
                    if (['rect', 'ellipse', 'polygon'].includes(target.type) && !target.linkedText) {
                        document.getElementById('btn_add_text_to_shape').click();
                    }
                    return true;
                },
                actionName: 'addText',
                render: function(ctx, left, top, styleOverride, fabricObject) {
                    if (['rect', 'ellipse', 'polygon'].includes(fabricObject.type) && !fabricObject.linkedText) {
                        const size = 40;
                        ctx.save();
                        ctx.translate(left, top);
                        ctx.drawImage(addTextImg, -size/2, -size/2, size, size);
                        ctx.restore();
                    }
                },
                cornerSize: 40
            });
"""
content = content.replace("controls.flipY = new fabric.Control({", add_text_control_code + "\n            controls.flipY = new fabric.Control({")

# 3. Prevent clicking invisible addText control by overriding object controls on selection
selection_code = """
        canvas.on('selection:created', updateObjectControls);
        canvas.on('selection:updated', updateObjectControls);
        
        function updateObjectControls(e) {
            const obj = e.selected[0];
            if (!obj) return;
            if (['rect', 'ellipse', 'polygon'].includes(obj.type) && !obj.linkedText) {
                obj.setControlVisible('addText', true);
            } else {
                obj.setControlVisible('addText', false);
            }
        }
"""
content = content.replace("canvas.on('selection:created', (e) => {", selection_code + "\n        canvas.on('selection:created', (e) => {")

# 4. Implement btn_add_text_to_shape logic
logic_code = """
        document.getElementById('btn_add_text_to_shape').addEventListener('click', () => {
            const obj = canvas.getActiveObject();
            if (!obj || !['rect', 'ellipse', 'polygon'].includes(obj.type) || obj.linkedText) return;
            
            const txtColor = document.getElementById('setting_text_color').value;
            const txtBgColor = document.getElementById('setting_text_bg_color').value;
            const txtSize = parseInt(document.getElementById('setting_text_size').value) || 20;
            const isBold = document.getElementById('btn_text_bold').classList.contains('active');
            const isItalic = document.getElementById('btn_text_italic').classList.contains('active');
            const isUnderline = document.getElementById('btn_text_underline').classList.contains('active');
            
            const alignActive = document.querySelector('.btn-group .btn-align.active');
            const textAlign = alignActive ? alignActive.getAttribute('data-align') : 'center';

            const center = obj.getCenterPoint();
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
            obj.setControlVisible('addText', false);
            
            canvas.setActiveObject(textObj);
            showToolPanel('text');
            textObj.enterEditing();
            textObj.selectAll();
            canvas.requestRenderAll();
            saveHistory();
        });
"""
content = content.replace("document.getElementById('btn_action_copy').addEventListener('click', async () => {", logic_code + "\n        document.getElementById('btn_action_copy').addEventListener('click', async () => {")

# 5. Scaling restrictions to prevent text overflow and infinite expanding bug
scaling_restriction = """
        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const textObj = obj.linkedText;
                const minW = textObj.getScaledWidth() + 20;
                const minH = textObj.getScaledHeight() + 20;
                const currentW = obj.width * obj.scaleX;
                const currentH = obj.height * obj.scaleY;
                
                // Prevent infinite expansion on single axis resize by clamping scaling factors
                let newScaleX = obj.scaleX;
                let newScaleY = obj.scaleY;
                
                if (currentW < minW) newScaleX = minW / obj.width;
                if (currentH < minH) newScaleY = minH / obj.height;
                
                obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                textObj.set({ width: Math.max(minW, (obj.width * obj.scaleX) - 20) });
            }
        });
"""
content = content.replace("canvas.on('object:moving', (e) => {", scaling_restriction + "\n        canvas.on('object:moving', (e) => {")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Add text to shape feature injected.")
