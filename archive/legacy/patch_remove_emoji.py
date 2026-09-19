import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 1. Remove form_edit_emoji HTML
emoji_html_pattern = re.compile(r'<!-- 이모티콘 전용 폼 -->\s*<div id="form_edit_emoji".*?</div>\s*</div>', re.DOTALL)
content = emoji_html_pattern.sub('', content)

# 2. Remove isEmoji block in dblclick
dblclick_pattern = re.compile(r'if\s*\(isEmoji\)\s*\{\s*document\.getElementById\(\'form_edit_emoji\'\)\.style\.display\s*=\s*\'block\';\s*const currentSize.*?\}\s*else if\s*\(isImage\)\s*\{', re.DOTALL)
content = dblclick_pattern.sub('if (isImage) {', content)

# 3. Remove isEmoji block in applyObjectEdit
apply_pattern = re.compile(r'if\s*\(isEmoji\)\s*\{\s*const size = parseInt\(document\.getElementById\(\'edit_emoji_size\'\)\.value\);.*?\}\s*else if\s*\(isImage\)\s*\{', re.DOTALL)
content = apply_pattern.sub('if (isImage) {', content)

# 4. In dblclick, there's document.getElementById('form_edit_image').style.display = 'none';. Wait, we just want to make sure it's clean.
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
