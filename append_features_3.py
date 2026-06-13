import io
content = io.open('Capcraft_Features.md', 'r', encoding='utf-8').read()
content += "\n  - 추가 이슈 해결 (2026-06): 도형의 가장자리를 잡아 크기를 조절할 때 시각적 크기가 따라오지 않던 현상(스케일 초기화 버그) 및 텍스트 툴바(B, I, U, 정렬, 크기)가 전역 변수 충돌로 인해 작동하지 않던 문제를 해결함.\n"
io.open('Capcraft_Features.md', 'w', encoding='utf-8').write(content)
