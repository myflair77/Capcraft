with open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
    f.write('''
#### 텍스트 토글 패널 내 "투명도" 기능 추가 (2026-06-10 추가)
- **목적:** 텍스트 토글 패널(`.sub-panel#panel_text`)에 "투명도" 입력창을 추가하여, 전역 "환경설정"의 "입력창 투명도"와 동일하게 작동하도록 동기화함.
- **수정 사항:**
  - `index.html` 내 텍스트 패널 요소에 `<input type="number" id="text_bg_opacity_input">` 요소를 새로 추가.
  - 해당 입력창과 환경설정의 `set_txt_bg_opacity` 요소가 서로 연동되도록 `addEventListener('input')` 및 `addEventListener('change')` 이벤트 추가.
  - 앱 로드 및 `applySettings()` 호출 시 양쪽의 투명도 값이 동일하게 유지되도록 동기화 로직 보강.
''')
print('Successfully updated features document.')
