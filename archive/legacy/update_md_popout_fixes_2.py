import io
with io.open('Capcraft_Features.md', 'a', encoding='utf-8') as f:
    f.write('\n## 팝아웃 기능 3D 원근감 렌더링 복원 및 UI 개선 (2026-06)\n')
    f.write('- **팝아웃 3D 원근감 복원 및 외곽선 정밀 매칭:** 이전 수정에서 `skewX`/`skewY`를 사용하여 외곽선을 맞추려다 손실된 3D 원근감(가까운 쪽은 커지고 먼 쪽은 작아지는 원근 효과)을 `regeneratePopoutBase` 내부에 투영 렌더링을 직접 베이킹하는 방식으로 완벽히 복원함. 이를 통해 3D 원근감이 살아있으면서도 Fabric.js의 선택 외곽선(bounding box)이 투영된 최종 이미지의 크기와 한 치의 오차도 없이 딱 들어맞도록 구현함.\n')
    f.write('- **팝아웃 속성 토글창(sub_toolbar) 위치 정렬:** 토글창이 캔버스 중앙(`left: 50%`)에 치우쳐 있던 문제를 수정하여, 상단바의 "텍스트" 버튼(`btn_text`)의 왼쪽 라인과 일치하도록 정렬 기준 위치를 변경함.\n')
    f.write('- **팝아웃 테두리 두께 변경 오류 수정:** 속성창에서 테두리 두께(`popout_border`)를 변경할 때 캔버스에 즉각 반영되지 않던 문제를 `regeneratePopoutBase` 이벤트 트리거 콜백 함수를 정상적으로 연결하여 실시간으로 반영되도록 해결함.\n')
