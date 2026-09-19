import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject a fresh, clean popoutReviver at the global scope
# A good place is right before `window.applySettings`
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
content = re.sub(r'canvas\.loadFromJSON\(([^,]+),\s*\(\)\s*=>\s*\{', r'canvas.loadFromJSON(\1, () => {', content)
content = content.replace("canvas.loadFromJSON(jsonToLoad, () => {", "canvas.loadFromJSON(jsonToLoad, () => {")

# Actually we need to make sure loadFromJSON passes popoutReviver
# `loadHistoryState` uses `state`
content = content.replace('canvas.loadFromJSON(state, function () {', 'canvas.loadFromJSON(state, function () {')

# Wait, `index.html` has canvas.loadFromJSON calls.
# Let's see them.
"
