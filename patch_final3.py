import io
import re

content = io.open('index.html', 'r', encoding='utf-8').read()

# 1. Fix syncShapeToText
old_sync = r"if \(clamped\) \{\s*shape\.set\(\{ scaleX: newScaleX, scaleY: newScaleY \}\);\s*if \(transform\) \{\s*const fixedPoint = shape\.getPointByOrigin\(transform\.originX, transform\.originY\);\s*shape\.setPositionByOrigin\(fixedPoint, transform\.originX, transform\.originY\);\s*\}\s*\}"
new_sync = """if (clamped) {
                if (transform) {
                    const fixedPoint = shape.getPointByOrigin(transform.originX, transform.originY);
                    shape.set({ scaleX: newScaleX, scaleY: newScaleY });
                    shape.setPositionByOrigin(fixedPoint, transform.originX, transform.originY);
                } else {
                    shape.set({ scaleX: newScaleX, scaleY: newScaleY });
                }
            }"""
content = re.sub(old_sync, new_sync, content)

# 2. Add canvas.uniformScaling = true
content = content.replace("const canvas = new fabric.Canvas('mainCanvas', {", "const canvas = new fabric.Canvas('mainCanvas', {\n            uniformScaling: true,")

io.open('index.html', 'w', encoding='utf-8').write(content)
print('Patched successfully')
