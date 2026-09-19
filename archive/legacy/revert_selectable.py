import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Revert selectable: false to selectable: true in btn_add_text_to_shape
    content = content.replace("selectable: false, // 단독 선택 불가 (도형 종속)", "selectable: true,")
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Reverted selectable to true.")

if __name__ == '__main__':
    main()
