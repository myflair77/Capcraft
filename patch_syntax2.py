import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the stray bracket that caused SyntaxError at line 3273
content = content.replace('syncFabricContainerSize();        }', 'syncFabricContainerSize();')

# 2. Completely remove any existing popoutReviver definitions
# Since it might be malformed, I'll use regex to remove anything that looks like it.
# Wait, let's just find "function popoutReviver" and remove the block manually to be safe.
# Or better, just use regex carefully
content = re.sub(r'\s*function popoutReviver\(o, obj\) \{[\s\S]*?o\[p\] !== undefined[\s\S]*?\}\s*\}', '', content)

# Also remove the broken one I might have injected
content = re.sub(r'\s*function popoutReviver\(o, obj\) \{[\s\S]*?\}\n', '\n', content)

# 3. Inject a fresh, clean popoutReviver at the global scope
# A good place is right before `window.applySettings`
clean_reviver = """
        function popoutReviver(o, obj) {
            if (o.isPopout) {
                const props = ['isPopout', 'popoutBorder', 'popoutBorderColor', 'popoutShadow', 'popoutShadowColor', 'popoutLineWeight', 'popoutLineColor', 'tiltX', 'tiltY', 'showConnectionLine', 'linkedOriginalId', 'linkedLineId', '_croppedBgDataUrl'];
                props.forEach(p => { if (o[p] !== undefined) obj[p] = o[p]; });
            }
        }
"""

content = content.replace('window.applySettings = function () {', clean_reviver + '\n        window.applySettings = function () {')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Syntax error and popoutReviver repaired!")
