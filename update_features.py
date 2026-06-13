import io
content = io.open('Capcraft_Features.md', 'r', encoding='utf-8').read()
# Find and replace the section
idx = content.find('### 2026-06-07')
if idx == -1:
    print('Section not found')
else:
    # Replace from that point to end
    new_section = """### 2026-06-07 도형 세로 길이 조절 및 텍스트 블록 설정 개선

#### 도형 세로 크기 조절 근본 수정
- **`uniformScaling: false`로 변경:** `uniformScaling: true`는 모든 핸들(상/하/좌/우 포함)이 비율 유지 모드로 동작하여 세로만 독립 조절이 불가능했음. `false`로 변경하여 상/하변 핸들은 세로만, 좌/우변 핸들은 가로만 독립적으로 조절 가능하도록 수정.
- **`object:scaling` 이벤트에서 `originalWidth/Height` 매 프레임 덮어쓰기 제거:** 기존에는 드래그 중 매 프레임마다 `originalWidth/Height`를 현재 값으로 갱신하여, 최소 크기 제한(clamp)의 기준점이 유실되는 버그 존재. 초기 생성 시점의 값만 보존하도록 수정.
- **`object:modified`에서 linkedText가 있는 도형의 `normalizeScale` 건너뛰기:** `normalizeScale`은 오브젝트를 재생성하여 `linkedText` 바인딩이 끊어지는 심각한 문제 존재. 대신 `rect`는 `width/height`에, `ellipse`는 `rx/ry`에, `polygon`은 `points` 좌표에 scale을 직접 반영(bake)하고 scale을 1로 리셋하는 방식 적용.
- **`syncShapeToText` 함수 단순화:** 복잡한 수학적 오프셋 계산(dx/dy/rad) 대신, 도형 타입별 텍스트 영역 비율(`textAreaFactor`, `heightFactor`)을 사용하여 최소 가로/세로 크기 제한만 적용하는 깔끔한 구조로 재작성.

#### 텍스트 자동 확대/축소 및 줄바꿈
- **`textObj.on('changed')` 핸들러 개선:** `originalHeight * scaleY` 대신 현재 `height * scaleY`를 사용하여, `normalizeScale` 후(scale=1, height=실제크기) 정확한 높이 비교가 되도록 수정.
- **`_initHeight` 속성 추가:** 글상자 생성 시점의 시각적 높이를 저장하여, 텍스트를 지울 때 이 높이까지만 자동 축소되도록 복원 로직 적용.
- **마름모/타원 내부 텍스트 영역:** `cos(π/4)` (약 0.707) 비율로 텍스트 영역 너비/높이를 계산하여 도형 경계 안에 텍스트가 머무르도록 보장.

#### 텍스트 블록 선택 서식 적용 수정
- 색상 팔레트(.palette-cell) 및 컬러 버튼에 `mousedown` 이벤트 시 `e.preventDefault()`를 추가하여 텍스트 편집 중 포커스가 유실되지 않도록 수정.
- `updateActiveText` 함수에서 `targetText.dirty = true; targetText.initDimensions();` 호출을 추가하여 선택 영역 서식이 즉시 반영되도록 개선.
"""
    content = content[:idx] + new_section
    io.open('Capcraft_Features.md', 'w', encoding='utf-8').write(content)
    print('Updated!')
