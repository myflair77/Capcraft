import io
content = io.open('Capcraft_Features.md', 'r', encoding='utf-8').read()
addition = """
#### 모든 개체의 세로 길이 조절 근본 수정 (2026-06-07 추가)
- **근본 원인:** `cropX`/`cropY` 함수가 `mt`(상변), `mb`(하변), `ml`(좌변), `mr`(우변) 핸들의 `actionHandler`를 덮어쓰고 있었음. 이 함수 내부에서 `!target.isMediaImage && target.type !== 'image'` 조건으로 분기하는데, 이모티콘이 `fabric.Image`로 생성되어 `type === 'image'`이므로 crop(자르기) 로직으로 진입하여 스케일링 대신 자르기만 실행됨.
- **수정:** 조건을 `!target.isMediaImage`로 변경하여, **오직 `isMediaImage: true`인 미디어 이미지만** crop 동작을 수행하고, 이모티콘(`isEmoji`)·도형·텍스트 등 나머지 모든 개체는 표준 `scalingX`/`scalingY`로 세로/가로 독립 조절이 가능하도록 수정.
"""
content += addition
io.open('Capcraft_Features.md', 'w', encoding='utf-8').write(content)
print('Done')
