import codecs
import re

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# Match the end of receiveCapturedImage function loosely
pattern = re.compile(r"(commitLoadToCanvas\(img, img\.width, img\.height, null\);\s*// [^\n]+ 자동 호출됨\s*\n\s*\}\);)", re.MULTILINE)

new_text = r"""\1
                    document.getElementById('btn_tool_shape').click();
                    const rectBtn = document.querySelector('#shape_type_group button[data-val="rect"]');
                    if (rectBtn) rectBtn.click();"""

if pattern.search(content):
    content = pattern.sub(new_text, content)
    with codecs.open('index.html', 'w', 'utf-8') as f:
        f.write(content)
    print('Patch applied successfully')
else:
    print('Failed to find old_recv')
