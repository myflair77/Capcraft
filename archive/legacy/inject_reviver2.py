import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject a fresh, clean popoutReviver at the global scope
clean_reviver = """
        window.popoutReviver = function(o, obj) {
            if (o.isPopout) {
                const props = ['isPopout', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'tiltX', 'tiltY', 'showConnectionLine', 'linkedOriginalId', 'linkedLineId', '_croppedBgDataUrl'];
                props.forEach(p => { if (o[p] !== undefined) obj[p] = o[p]; });
            }
        };
"""

content = content.replace('window.applySettings = function () {', clean_reviver + '\n        window.applySettings = function () {')

# 2. Fix the loadFromJSON calls to use window.popoutReviver
# Replace canvas.loadFromJSON(json, () => { with canvas.loadFromJSON(json, () => { ... }, window.popoutReviver);
# Note that loadHistoryState uses `state.objects` currently in my version of index.html?
# Let's check what it uses. Wait, earlier I found it used `state.objects`.
content = content.replace("canvas.loadFromJSON(jsonToLoad, () => {", "canvas.loadFromJSON(jsonToLoad, () => {")

# To be safe, I'll regex replace `});` at the end of loadFromJSON with `}, window.popoutReviver);`
# Actually, the most robust way is:
content = re.sub(r'(canvas\.loadFromJSON\([^\)]+,\s*\(\)\s*=>\s*\{[\s\S]*?)\}\);', r'\1}, window.popoutReviver);', content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Injected popoutReviver and patched loadFromJSON!")
