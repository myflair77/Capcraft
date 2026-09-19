import codecs

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# 1. Fix object:scaling to use independent axis clamping
old_scaling = """                if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                    const tw = textObj.getScaledWidth();
                    const th = textObj.getScaledHeight();
                    const ratio = (tw / currentW) + (th / currentH);
                    if (ratio > 0.85) {
                        const f = ratio / 0.85; newScaleX *= f; newScaleY *= f;
                    }
                } else if (obj.type === 'ellipse') {
                    const tw = textObj.getScaledWidth();
                    const th = textObj.getScaledHeight();
                    const ratioSq = Math.pow(tw / currentW, 2) + Math.pow(th / currentH, 2);
                    if (ratioSq > 0.8) {
                        const f = Math.sqrt(ratioSq / 0.8); newScaleX *= f; newScaleY *= f;
                    }
                } else {
                    if (currentW < minW) newScaleX = minW / obj.width;
                    if (currentH < minH) newScaleY = minH / obj.height;
                }
                
                obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                // Do not auto-expand width of text when scaling shape, keep it proportional or let the user wrap
                textObj.set({ width: Math.max(textObj.width, (obj.width * newScaleX) / (obj.type==='polygon'?1.5:1.2)) });"""

new_scaling = """                let reqMinW = minW;
                let reqMinH = minH;
                if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                    reqMinW = textObj.getScaledWidth() * 1.5;
                    reqMinH = textObj.getScaledHeight() * 1.5;
                } else if (obj.type === 'ellipse') {
                    reqMinW = textObj.getScaledWidth() * 1.4;
                    reqMinH = textObj.getScaledHeight() * 1.4;
                }
                if (currentW < reqMinW) newScaleX = reqMinW / obj.width;
                if (currentH < reqMinH) newScaleY = reqMinH / obj.height;
                
                obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                
                // Do not auto-expand text width when scaling shape; user can let it wrap
                const twBase = obj.width * newScaleX;
                let newTw = twBase - 20;
                if (obj.type === 'polygon' && obj.points && obj.points.length === 4) newTw = twBase / 1.5;
                else if (obj.type === 'ellipse') newTw = twBase / 1.4;
                textObj.set({ width: Math.max(textObj.width, newTw) });"""

content = content.replace(old_scaling, new_scaling)

# 2. Add object:rotating listener
old_rotating = """        canvas.on('object:moving', (e) => {"""
new_rotating = """        canvas.on('object:rotating', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const center = obj.getCenterPoint();
                obj.linkedText.set({ left: center.x, top: center.y, angle: obj.angle });
                obj.linkedText.setCoords();
            }
        });
        
        canvas.on('object:moving', (e) => {"""

content = content.replace(old_rotating, new_rotating)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(content)

print("Patch 6 applied!")
