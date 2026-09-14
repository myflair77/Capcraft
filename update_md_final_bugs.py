import os

text = """
- **팝아웃 Undo/Redo 배경 복구 및 커스텀 속성 직렬화 개선:** JSON 복원 시 `_croppedBgDataUrl`를 비동기적으로 로드한 뒤 팝아웃 원근감/그림자 상태(`regeneratePopoutBase`)를 다시 트리거하도록 안전하게 개선하여, 히스토리(Undo/Redo) 탐색이나 프로그램 재시작 시 팝아웃 개체가 사라지던 치명적인 문제 완전 해결.
- **팝아웃 그림자 강도 실시간 반영 수정:** 속성창에서 `popout_shadow` 수치를 변경했을 때 `applyPopoutTilt`가 아닌 `regeneratePopoutBase` 이벤트 트리거 함수와 바인딩되도록 연결 고리를 교체하여 그림자 농도가 캔버스에 즉각 렌더링되게 개선.
"""

with open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
    f.write(text)
print("Updated documentation.")
