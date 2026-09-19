import io
content = io.open('index.html', 'r', encoding='utf-8').read()

old_logic = """            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집
            if (!activeTool && o.target && o.target.linkedShape) {"""

new_logic = """            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집
            const isControl = canvas._currentTransform && canvas._currentTransform.action && canvas._currentTransform.action !== 'drag';
            if (!activeTool && o.target && o.target.linkedShape && !isControl) {"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    print("Patched linkedShape")
else:
    print("linkedShape not found")

old_logic2 = """            } else if (!activeTool && o.target && o.target.linkedText) {"""

new_logic2 = """            } else if (!activeTool && o.target && o.target.linkedText && !isControl) {"""

if old_logic2 in content:
    content = content.replace(old_logic2, new_logic2)
    print("Patched linkedText")
else:
    print("linkedText not found")

io.open('index.html', 'w', encoding='utf-8').write(content)
