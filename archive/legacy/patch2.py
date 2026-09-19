import codecs
import re

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# 1. Update controls
# flipX
content = re.sub(
    r"(controls\.flipX = new fabric\.Control\(\{.*?offsetX:\s*)-75(.*?)cornerSize:\s*40",
    r"\g<1>-100\g<2>cornerSize: 60, transparentCorners: false",
    content, flags=re.DOTALL
)

# flipY
content = re.sub(
    r"(controls\.flipY = new fabric\.Control\(\{.*?offsetX:\s*)-25(.*?)cornerSize:\s*40",
    r"\g<1>-50\g<2>cornerSize: 60, transparentCorners: false",
    content, flags=re.DOTALL
)

# sendBack
content = re.sub(
    r"(controls\.sendBack = new fabric\.Control\(\{.*?offsetX:\s*)25(.*?)cornerSize:\s*40",
    r"\g<1>0\g<2>cornerSize: 60, transparentCorners: false",
    content, flags=re.DOTALL
)

# bringFront
content = re.sub(
    r"(controls\.bringFront = new fabric\.Control\(\{.*?offsetX:\s*)75(.*?)cornerSize:\s*40",
    r"\g<1>50\g<2>cornerSize: 60, transparentCorners: false",
    content, flags=re.DOTALL
)

# addText
content = re.sub(
    r"(controls\.addText = new fabric\.Control\(\{.*?offsetX:\s*)-125(.*?)cornerSize:\s*40",
    r"\g<1>100\g<2>cornerSize: 60, transparentCorners: false",
    content, flags=re.DOTALL
)

# 2. Text auto-resizing
# Find btn_add_text_to_shape listener
resize_logic = """
            // 도형 원본 크기 백업
            obj.originalScaleX = obj.scaleX;
            obj.originalScaleY = obj.scaleY;
            obj.originalWidth = obj.width;
            obj.originalHeight = obj.height;

            textObj.on('changed', function() {
                const shape = this.linkedShape;
                if (!shape) return;
                
                const padding = 20;
                const reqW = this.width + padding;
                const reqH = this.height + padding;

                const baseW = shape.originalWidth * shape.originalScaleX;
                const baseH = shape.originalHeight * shape.originalScaleY;

                let newW = Math.max(baseW, reqW);
                let newH = Math.max(baseH, reqH);

                // shape.scaleX * shape.width = newW => scaleX = newW / shape.width
                shape.set({
                    scaleX: newW / shape.originalWidth,
                    scaleY: newH / shape.originalHeight
                });
                
                shape.setCoords();
                if (shape.canvas) {
                    shape.canvas.requestRenderAll();
                }
            });
"""

old_btn_add_text = "canvas.add(textObj);"
new_btn_add_text = old_btn_add_text + resize_logic

if old_btn_add_text in content and "obj.originalScaleX = obj.scaleX;" not in content:
    content = content.replace(old_btn_add_text, new_btn_add_text)
else:
    print("Auto-resize logic already present or failed to find injection point.")

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(content)

print("Patch applied")
