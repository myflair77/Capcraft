import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CSS for pin to top right
content = content.replace("bottom: 2px; right: 2px;", "top: 2px; right: 2px;")

# 2. Add pin to text and remove from eraser
text_pattern = re.compile(r'(<button[^>]*id="btn_tool_text"[^>]*>.*?</button>)', re.DOTALL)
match = text_pattern.search(content)
if match and 'class="pin-icon"' not in match.group(1):
    content = text_pattern.sub(lambda m: m.group(1).replace('</button>', '<span class="pin-icon" title="고정하기">📌</span></button>'), content)

eraser_pattern = re.compile(r'(<button[^>]*id="btn_tool_eraser"[^>]*>.*?)</button>', re.DOTALL)
content = eraser_pattern.sub(lambda m: re.sub(r'<span class="pin-icon".*?</span>', '', m.group(1)) + '</button>', content)

# 3. Add Rhombus button
btn_rect = '<button class="active" data-val="rect">직사각형</button>'
btn_rhombus = '<button class="active" data-val="rect">직사각형</button>\n                <button data-val="rhombus">마름모</button>'
if 'data-val="rhombus"' not in content:
    content = content.replace(btn_rect, btn_rhombus)

# 4. Add Rhombus mouse down
mouse_down_target = """} else if (shapeType === 'ellipse') { 
                        currentShape = new fabric.Ellipse({ left: origX, top: origY, originX: 'center', originY: 'center', fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, isTemp: true }); canvas.add(currentShape); 
                    }"""
mouse_down_rhombus = """} else if (shapeType === 'ellipse') { 
                        currentShape = new fabric.Ellipse({ left: origX, top: origY, originX: 'center', originY: 'center', fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, isTemp: true }); canvas.add(currentShape); 
                    } else if (shapeType === 'rhombus') {
                        currentShape = new fabric.Polygon([{x:0, y:0}, {x:1, y:0}, {x:1, y:1}, {x:0, y:1}], { left: origX, top: origY, fill: fColor, stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineJoin: 'miter', isTemp: true, objectCaching: false }); 
                        canvas.add(currentShape);
                    }"""
if "shapeType === 'rhombus'" not in content:
    content = content.replace(mouse_down_target, mouse_down_rhombus)

# 5. Add Rhombus mouse move
mouse_move_target = """else if (shapeType === 'ellipse') { currentShape.set({ rx: Math.abs(origX - pointer.x) / 2, ry: Math.abs(origY - pointer.y) / 2 }); currentShape.set({ left: (origX + pointer.x) / 2, top: (origY + pointer.y) / 2 }); } 
                else if (isNormalLine) {"""
mouse_move_rhombus = """else if (shapeType === 'ellipse') { currentShape.set({ rx: Math.abs(origX - pointer.x) / 2, ry: Math.abs(origY - pointer.y) / 2 }); currentShape.set({ left: (origX + pointer.x) / 2, top: (origY + pointer.y) / 2 }); } 
                else if (shapeType === 'rhombus') {
                    let minX = Math.min(origX, pointer.x); let maxX = Math.max(origX, pointer.x);
                    let minY = Math.min(origY, pointer.y); let maxY = Math.max(origY, pointer.y);
                    let w = maxX - minX; let h = maxY - minY;
                    if(w > 0 && h > 0) {
                        currentShape.set({ left: minX, top: minY, width: w, height: h, points: [{x: w/2, y: 0}, {x: w, y: h/2}, {x: w/2, y: h}, {x: 0, y: h/2}] });
                        currentShape._calcDimensions(); currentShape.pathOffset = {x: w/2, y: h/2}; currentShape.setCoords();
                    }
                }
                else if (isNormalLine) {"""
if "else if (shapeType === 'rhombus')" not in content:
    content = content.replace(mouse_move_target, mouse_move_rhombus)

# 6. Add deactivateActiveTool for Text
text_up_target = "if(activeTool === 'text' && currentShape) { currentShape.isTemp = false; updateObjectSelectability(); saveHistory(); currentShape = null; }"
text_up_replacement = "if(activeTool === 'text' && currentShape) { currentShape.isTemp = false; updateObjectSelectability(); saveHistory(); deactivateActiveTool(); currentShape = null; }"
content = content.replace(text_up_target, text_up_replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Rhombus added and Pin fixed.")
