import io
with io.open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
    f.write('\n## 팝아웃 개체 직렬화/역직렬화(Undo/Redo 및 자동저장) 복구 (2026-06)\n')
    f.write('- **팝아웃 속성 보존:** Fabric.js의 기본 객체 직렬화(`toObject`) 시 누락되던 팝아웃 전용 커스텀 속성들(`isPopout`, `tiltX`, `tiltY`, `popoutBorder` 등)을 직렬화 배열에 명시적으로 추가하여, Undo/Redo 시 데이터가 증발하지 않도록 수정함.\n')
    f.write('- **참조 객체 연결(Link) 복원:** 팝아웃 개체와 그 모체인 원본 도형(`linkedOriginal`), 연결선(`linkedLine`) 간의 양방향 연결을 유지하기 위해 생성 시 고유 ID를 부여하여 직렬화에 포함함. 불러오기 시(`finalizeLoad`) ID를 대조하여 잃어버린 연결 고리를 자동으로 재맵핑하는 로직 구현.\n')
    f.write('- **3D 렌더링 상태 복구:** 팝아웃의 기본 크롭 이미지(`_croppedBg`)를 DataURL 형태로 백업 저장하고, 불러올 때 이를 읽어 임시 캔버스(Canvas) 객체로 복원한 뒤 `applyPopoutTilt`를 실행시켜 저장 당시의 사실적인 3D 렌더링을 완전히 동일하게 복구하도록 구현.\n')
