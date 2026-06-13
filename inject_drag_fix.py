import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to find the blocks where we enter editing for linkedShape/linkedText
    # and add initMouseMoveHandler() and canvas._currentTransform = null;
    
    target_text1 = """                    const textTarget = o.target;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    textTarget.setCursorByClick(o.e);
                    // 삭제: canvas._currentTransform = null; (드래그 버그 방지)
                    canvas.requestRenderAll();"""
    
    replacement1 = """                    const textTarget = o.target;
                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    
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
                    
                    canvas.requestRenderAll();"""

    target_text2 = """                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    textTarget.setCursorByClick(o.e);
                    canvas.requestRenderAll();"""
                    
    replacement2 = """                    canvas.setActiveObject(textTarget);
                    textTarget.enterEditing();
                    
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
                    
                    canvas.requestRenderAll();"""

    if "textTarget.initMouseMoveHandler()" not in content:
        content = content.replace(target_text1, replacement1)
        content = content.replace(target_text2, replacement2)
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched index.html for initMouseMoveHandler and _currentTransform.")
    else:
        print("Already patched.")

if __name__ == '__main__':
    main()
