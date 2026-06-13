import re

def main():
    append_text = """  27. 도형 내 텍스트 편집 중 드래그 블록 선택 및 조작 불가 버그 수정:
      - 도형 내 글상자가 이미 편집 모드(커서 깜빡임)에 진입한 상태에서, 마우스 클릭으로 텍스트를 드래그하여 블록을 지정하거나 커서를 다른 위치로 이동시키려 할 때 다시 도형이 선택되며 편집이 해제되던 버그를 해결했습니다.
      - 텍스트가 편집 모드일 경우 커스텀 `mouse:down` 이벤트가 이를 감지하여 조기에 종료(return)하도록 함으로써, Fabric.js의 내장 텍스트 이벤트 처리 로직이 온전히 실행되어 자연스러운 블록 지정 및 편집이 가능해졌습니다.
"""
    with open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
        f.write(append_text)

if __name__ == '__main__':
    main()
