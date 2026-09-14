import re

filepath = 'index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace JSON.stringify(canvas)
custom_props = "['id', 'isPopout', '_croppedBgDataUrl', 'linkedOriginalId', 'linkedLineId', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'showConnectionLine', 'tiltX', 'tiltY', 'skewX', 'skewY', 'isEditing']"

content = content.replace('JSON.stringify(canvas)', f'JSON.stringify(canvas.toJSON({custom_props}))')

# Also fix the manual JSON.stringify(canvas.toJSON([...])) on line 4587
# original: JSON.stringify(canvas.toJSON(['width', 'height', 'backgroundColor']))
content = content.replace("JSON.stringify(canvas.toJSON(['width', 'height', 'backgroundColor']))", f"JSON.stringify(canvas.toJSON(['width', 'height', 'backgroundColor', 'id', 'isPopout', '_croppedBgDataUrl', 'linkedOriginalId', 'linkedLineId', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'showConnectionLine', 'tiltX', 'tiltY', 'skewX', 'skewY', 'isEditing']))")


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched JSON.stringify')
