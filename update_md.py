import io
content = io.open('Capcraft_Features.md', 'r', encoding='utf-8').read()
content += '''
    - 도형의 상변/하변 크기 조절 시 무효화되던 현상 수정 (`reqH` 상수 재할당 버그 및 `setPositionByOrigin` 미적용 문제 해결)
    - 텍스트 입력 및 글꼴 변경 시 높이가 도형 크기에 실시간 연동되도록 `changed` 이벤트 동기화 강화
    - 블록 지정 후 컬러 피커 사용 시 발생하던 `ReferenceError` 버그 픽스 및 정렬(Align) 속성이 부분 서식으로 오적용되던 문제 수정
'''
io.open('Capcraft_Features.md', 'w', encoding='utf-8').write(content)
