import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

reviver_code = """
        function popoutReviver(o, obj) {
            if (o.isPopout) {
                const props = ['isPopout', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'tiltX', 'tiltY', 'showConnectionLine', 'linkedOriginalId', 'linkedLineId', '_croppedBgDataUrl'];
                props.forEach(p => { if (o[p] !== undefined) obj[p] = o[p]; });
            }
        }
"""

if 'function popoutReviver' not in content:
    content = content.replace('function finalizeLoad() {', reviver_code + '\n        function finalizeLoad() {')

content = re.sub(r'canvas\.loadFromJSON\(([^,]+),\s*\(\)\s*=>\s*\{', r'canvas.loadFromJSON(\1, () => {', content)
# Actually, it's easier to just do:
content = content.replace("canvas.loadFromJSON(jsonToLoad, () => {", "canvas.loadFromJSON(jsonToLoad, () => {")
# Wait, replacing the end of the loadFromJSON block is hard with regex because it spans multiple lines.
# Let's just find the closing bracket of the callback and add `, popoutReviver`? No, reviver is the 3rd argument.
# canvas.loadFromJSON(json, callback, reviver)
