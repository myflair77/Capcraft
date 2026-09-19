with open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
    f.write('''
#### 텍스트 개체 더블클릭 시 속성 수정 창 비활성화 (2026-06-10 추가)
- **목적:** 텍스트 개체는 자체에서 직접 편집이 가능하므로, 불필요하게 '개체 속성 수정' 팝업 창이 나타나지 않도록 개선함.
- **수정 사항:**
  - `index.html`의 캔버스 더블클릭 이벤트 핸들러(`canvas.on('mouse:dblclick')`) 내에 `if (isText && !isEmoji) return;` 조건을 추가.
  - 이모지 개체가 아닌 일반 텍스트 개체를 더블클릭할 경우 즉시 핸들러를 종료하여 속성 창이 나타나지 않게 함.
''')
print('Successfully updated features document.')
