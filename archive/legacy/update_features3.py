import io
content = io.open('Capcraft_Features.md', 'r', encoding='utf-8').read()
addition = """
#### Textbox 컨트롤 얕은 복사(shallow clone) 문제 수정 (2026-06-07 추가)
- **근본 원인:** `fabric.util.object.clone(controls)`는 1단계만 복사하는 얕은 복사(shallow clone)임. 따라서 `fabric.Textbox.prototype.controls.tl`은 원본 `controls.tl`과 **동일한 객체 참조**를 공유함. Textbox 전용으로 `tl.actionHandler = changeWidth`를 설정하면, 원본 `controls.tl.actionHandler`까지 함께 변경되어 **모든 개체(도형, 이모티콘, 이미지 등)의 꼭짓점 핸들러가 `changeWidth`(가로만 변경)**로 바뀌는 심각한 버그 발생.
- **수정:** `Object.keys(controls).forEach(key => { textboxControls[key] = new fabric.Control(Object.assign({}, controls[key])); })` 방식으로 각 컨트롤 객체를 개별적으로 깊은 복사하여 Textbox 전용 controls 세트를 완전히 분리. 이로써 Textbox의 핸들러 변경이 다른 개체 타입의 핸들러에 영향을 미치지 않음.
"""
content += addition
io.open('Capcraft_Features.md', 'w', encoding='utf-8').write(content)
print('Done')
