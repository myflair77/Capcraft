import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    old_mousedown = """            // 텍스트가 이미 편집 중인 상태라면 Fabric.js 내장 로직(드래그 블록지정, 커서 이동 등)에 위임
            if (o.target && (o.target.isEditing || (o.target.type === 'textbox' && o.target.isEditing))) {
                return;
            }"""

    new_mousedown = """            // 텍스트가 이미 편집 중인 상태라면 Fabric.js 내장 로직(드래그 블록지정, 커서 이동 등)에 위임
            if (o.target && (o.target.isEditing || (o.target.type === 'textbox' && o.target.isEditing))) {
                canvas._currentTransform = null; // 드래그 시 도형 이동(4방향 커서) 방지
                return;
            }"""

    content = content.replace(old_mousedown, new_mousedown)

    # Clean up the bloated enterEditing calls I added
    old_enter1 = """                    textTarget.enterEditing();
                    
                    // 커서 위치 지정
                    if (typeof textTarget.setCursorByClick === 'function') {
                        textTarget.setCursorByClick(o.e);
                    }
                    
                    // 드래그 블록 선택(텍스트 하이라이트) 활성화
                    if (typeof textTarget.initMouseMoveHandler === 'function') {
                        textTarget.initMouseMoveHandler();
                    }
                    
                    // 이동(4방향 커서) 트랜스폼 취소
                    canvas._currentTransform = null;
                    
                    canvas.requestRenderAll();
                    return;"""

    new_enter1 = """                    textTarget.enterEditing();
                    canvas._currentTransform = null;
                    canvas.requestRenderAll();
                    return;"""
                    
    content = content.replace(old_enter1, new_enter1)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed mouse:down logic.")

if __name__ == '__main__':
    main()
