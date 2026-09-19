import os

filepath = r"c:\Coding\Capcraft\Capcraft_Features.md"
with open(filepath, "a", encoding="utf-8") as f:
    f.write("\n\n### 팝아웃(Popout) 개체 개선\n")
    f.write("- **내부 영역 마스킹 정확도 개선**: `regeneratePopoutBase`에서 팝아웃 개체를 렌더링할 때 원본 도형의 `originX`/`originY`를 임시로 `center`로 조정하여 중심축이 일치하지 않아 잘려나온 이미지가 어긋나는 현상 수정.\n")
    f.write("- **회전 시 그림자 중첩 및 왜곡 방지**: 팝아웃 개체를 가로축(Tilt X) 및 세로축(Tilt Y)으로 회전할 때, 내부적으로 스트립 단위 스캔라인 렌더링 과정에서 그림자가 지속 중첩되어 오브젝트 앞쪽으로 튀어나오는 오류 수정. 이제 그림자는 최종 형태 렌더링 완료 시 단 한 번, 개체 뒤쪽에만 정확히 표시되도록 파이프라인(`_render`) 변경.\n")
    f.write("- **테두리 외곽 형성 및 치우침 현상 해결**: 팝아웃 테두리를 그릴 때 기존 방식(`source-over` 위에 테두리 그림)에서 다중 캔버스를 이용한 밑바탕(Outer stroke) 기법으로 변경. 테두리 두께를 2배로 그린 뒤 위에 내용물을 덮어씌움으로써 완벽하게 원개체 경계선 바깥(외곽)으로만 테두리가 형성되도록 개선.\n")
