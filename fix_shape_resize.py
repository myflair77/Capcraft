import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove the duplicate obj.on('scaling')
    dup_scaling = """            // 도형 수동 리사이징 시 텍스트 폭 자동 갱신
            obj.on('scaling', function() {
                if (this.linkedText) {
                    let pw = 20;
                    let sw = this.width * this.scaleX;
                    if (this.type === 'ellipse') {
                        sw = sw * Math.cos(Math.PI / 4);
                    } else if (this.type === 'polygon' && this.points && this.points.length === 4) {
                        sw = sw * 0.5;
                    }
                    sw = Math.max(50, sw - pw);
                    this.linkedText.set({ width: sw });
                    this.linkedText.fire('changed');
                }
            });"""
    content = content.replace(dup_scaling, "")

    # 2. Update global canvas.on('object:scaling')
    global_scaling_old = """        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const textObj = obj.linkedText;
                const minW = textObj.dynamicMinWidth || 50;
                const minH = textObj.calcTextHeight() + 20;
                const currentW = obj.width * obj.scaleX;
                const currentH = obj.height * obj.scaleY;
                
                let newScaleX = obj.scaleX;
                let newScaleY = obj.scaleY;
                let clamped = false;
                
                const minScaleX = minW / obj.width;
                const minScaleY = minH / obj.height;
                
                const isCorner = e.transform && ['tl', 'tr', 'bl', 'br'].includes(e.transform.corner);
                
                if (isCorner) {
                    if (currentW < minW || currentH < minH) {
                        let requiredRatioX = minScaleX / newScaleX;
                        let requiredRatioY = minScaleY / newScaleY;
                        let maxRatio = Math.max(requiredRatioX, requiredRatioY);
                        if (maxRatio > 1) {
                            newScaleX *= maxRatio;
                            newScaleY *= maxRatio;
                            clamped = true;
                        }
                    }
                } else {
                    if (currentW < minW) { newScaleX = minScaleX; clamped = true; }
                    if (currentH < minH) { newScaleY = minScaleY; clamped = true; }
                }
                
                if (clamped && e.transform) {
                    const originX = e.transform.originX;
                    const originY = e.transform.originY;
                    const fixedPoint = obj.getPointByOrigin(originX, originY);
                    
                    obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                    obj.setPositionByOrigin(fixedPoint, originX, originY);
                }
                
                const center = obj.getCenterPoint();
                textObj.set({ 
                    width: Math.max(minW, (obj.width * obj.scaleX) - 20),
                    left: center.x,
                    top: center.y,
                    angle: obj.angle
                });
                textObj.setCoords();
            }
        });"""

    global_scaling_new = """        canvas.on('object:scaling', (e) => {
            const obj = e.target;
            if (obj.linkedText) {
                const textObj = obj.linkedText;
                const minW = textObj.dynamicMinWidth || 50;
                let minH = textObj.calcTextHeight() + 20;
                
                let currentW = obj.width * obj.scaleX;
                let currentH = obj.height * obj.scaleY;
                
                let requiredShapeW = minW + 20;
                let requiredShapeH = minH;
                if (obj.type === 'ellipse') {
                    requiredShapeW = requiredShapeW / Math.cos(Math.PI / 4);
                    requiredShapeH = requiredShapeH / Math.sin(Math.PI / 4);
                } else if (obj.type === 'polygon' && obj.points && obj.points.length === 4) {
                    requiredShapeW = requiredShapeW / 0.5;
                    requiredShapeH = requiredShapeH / 0.5;
                }
                
                let newScaleX = obj.scaleX;
                let newScaleY = obj.scaleY;
                let clamped = false;
                
                const minScaleX = requiredShapeW / obj.width;
                const minScaleY = requiredShapeH / obj.height;
                
                const isCorner = e.transform && ['tl', 'tr', 'bl', 'br'].includes(e.transform.corner);
                
                if (isCorner) {
                    if (currentW < requiredShapeW || currentH < requiredShapeH) {
                        let requiredRatioX = minScaleX / newScaleX;
                        let requiredRatioY = minScaleY / newScaleY;
                        let maxRatio = Math.max(requiredRatioX, requiredRatioY);
                        if (maxRatio > 1) {
                            newScaleX *= maxRatio;
                            newScaleY *= maxRatio;
                            clamped = true;
                        }
                    }
                } else {
                    if (currentW < requiredShapeW) { newScaleX = minScaleX; clamped = true; }
                    if (currentH < requiredShapeH) { newScaleY = minScaleY; clamped = true; }
                }
                
                if (clamped && e.transform) {
                    const originX = e.transform.originX;
                    const originY = e.transform.originY;
                    const fixedPoint = obj.getPointByOrigin(originX, originY);
                    
                    obj.set({ scaleX: newScaleX, scaleY: newScaleY });
                    obj.setPositionByOrigin(fixedPoint, originX, originY);
                }
                
                let textTargetW = (obj.width * obj.scaleX);
                if (obj.type === 'ellipse') textTargetW *= Math.cos(Math.PI / 4);
                else if (obj.type === 'polygon' && obj.points && obj.points.length === 4) textTargetW *= 0.5;
                textTargetW = Math.max(minW, textTargetW - 20);
                
                const center = obj.getCenterPoint();
                textObj.set({ 
                    width: textTargetW,
                    left: center.x,
                    top: center.y,
                    angle: obj.angle
                });
                textObj.setCoords();
            }
        });"""

    content = content.replace(global_scaling_old, global_scaling_new)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed obj.on('scaling') and global object:scaling.")

if __name__ == '__main__':
    main()
