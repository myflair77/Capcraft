import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the mouse:down start
    target_str = "            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집\n"
    replacement_str = """            // 텍스트가 이미 편집 중인 상태라면 Fabric.js 내장 로직(드래그 블록지정, 커서 이동 등)에 위임
            if (o.target && (o.target.isEditing || (o.target.type === 'textbox' && o.target.isEditing))) {
                return;
            }
            
            // 도형 내 글상자: 첫 클릭은 도형 선택, 두 번째 클릭은 텍스트 편집
"""
    if "o.target.isEditing" not in content.split("canvas.on('mouse:down'")[1][:500]:
        content = content.replace(target_str, replacement_str)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched mouse:down to allow block selection.")
    else:
        print("Already patched.")

if __name__ == '__main__':
    main()
