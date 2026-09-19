import io

content = io.open('index.html', 'r', encoding='utf-8').read()

# 1. Add hoverCursor: 'move'
old_creation = """                selectable: true,
                evented: true,     // 클릭 이벤트는 받아야 함
                splitByGrapheme: true
            });"""

new_creation = """                selectable: true,
                evented: true,     // 클릭 이벤트는 받아야 함
                splitByGrapheme: true,
                hoverCursor: 'move'
            });"""

if old_creation in content:
    content = content.replace(old_creation, new_creation)
    print("Patched Textbox creation hoverCursor")
else:
    print("Warning: could not find Textbox creation")

# 2. Add event listeners for editing:entered and editing:exited
old_events = """            obj.linkedText = textObj;
            textObj.linkedShape = obj;
            
            canvas.add(textObj);"""

new_events = """            obj.linkedText = textObj;
            textObj.linkedShape = obj;
            
            textObj.on('editing:entered', function() {
                this.set('hoverCursor', 'text');
            });
            textObj.on('editing:exited', function() {
                this.set('hoverCursor', 'move');
            });
            
            canvas.add(textObj);"""

if old_events in content:
    content = content.replace(old_events, new_events)
    print("Patched Textbox events")
else:
    print("Warning: could not find Textbox events")

io.open('index.html', 'w', encoding='utf-8').write(content)
