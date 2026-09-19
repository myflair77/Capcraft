import os
import sys

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert functions
func_code = """
        let snapMarkerObj = null;
        function updateSnapMarker(canvas, point) {
            if (!point) {
                if (snapMarkerObj) { snapMarkerObj.set('opacity', 0); canvas.requestRenderAll(); }
                return;
            }
            if (!snapMarkerObj) {
                snapMarkerObj = new fabric.Circle({
                    left: point.x, top: point.y, radius: 4, originX: 'center', originY: 'center',
                    fill: 'rgba(59, 130, 246, 0.8)', stroke: 'white', strokeWidth: 1.5,
                    selectable: false, evented: false, isTemp: true, objectCaching: false
                });
                canvas.add(snapMarkerObj);
            } else {
                snapMarkerObj.set({ left: point.x, top: point.y, opacity: 1 });
                canvas.bringToFront(snapMarkerObj);
            }
            canvas.requestRenderAll();
        }

        function calculateBoundarySnap(pointer, canvas, currentShapeToIgnore) {
            const snapRadius = 15;
            let closestPoint = null;
            let minDist = snapRadius;
            const objects = canvas.getObjects();
            
            function distToSegment(px, py, x1, y1, x2, y2) {
                let l2 = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2);
                if (l2 === 0) return Math.hypot(px - x1, py - y1);
                let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
                t = Math.max(0, Math.min(1, t));
                return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
            }
            function closestPointOnSegment(px, py, x1, y1, x2, y2) {
                let l2 = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2);
                if (l2 === 0) return {x: x1, y: y1};
                let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
                t = Math.max(0, Math.min(1, t));
                return {x: x1 + t * (x2 - x1), y: y1 + t * (y2 - y1)};
            }

            for (let i = objects.length - 1; i >= 0; i--) {
                const obj = objects[i];
                if (obj === currentShapeToIgnore || obj === snapMarkerObj || obj.isArrowBody || obj.type === 'path' && obj.isTemp) continue;
                if (obj.linkedShape) continue; 
                if (obj.opacity === 0 || !obj.visible) continue;

                let matrix = obj.calcTransformMatrix();

                if (obj.type === 'ellipse') {
                    let invMatrix = fabric.util.invertTransform(matrix);
                    let localP = fabric.util.transformPoint(pointer, invMatrix);
                    let rx = obj.rx; let ry = obj.ry;
                    if (rx > 0 && ry > 0) {
                        let angle = Math.atan2(localP.y * rx, localP.x * ry);
                        let edgeLocalX = rx * Math.cos(angle);
                        let edgeLocalY = ry * Math.sin(angle);
                        let edgeGlobal = fabric.util.transformPoint({x: edgeLocalX, y: edgeLocalY}, matrix);
                        let dist = Math.hypot(pointer.x - edgeGlobal.x, pointer.y - edgeGlobal.y);
                        if (dist < minDist) { minDist = dist; closestPoint = edgeGlobal; }
                    }
                } else if (obj.type === 'polygon' && obj.points) {
                    let pts = obj.points.map(p => {
                        let localX = p.x - obj.pathOffset.x;
                        let localY = p.y - obj.pathOffset.y;
                        return fabric.util.transformPoint({x: localX, y: localY}, matrix);
                    });
                    for(let j=0; j<pts.length; j++) {
                        let p1 = pts[j]; let p2 = pts[(j+1)%pts.length];
                        let dist = distToSegment(pointer.x, pointer.y, p1.x, p1.y, p2.x, p2.y);
                        if (dist < minDist) { minDist = dist; closestPoint = closestPointOnSegment(pointer.x, pointer.y, p1.x, p1.y, p2.x, p2.y); }
                    }
                } else {
                    let w = obj.width; let h = obj.height;
                    let hw = w/2; let hh = h/2;
                    let ptsLocal = [ {x: -hw, y: -hh}, {x: hw, y: -hh}, {x: hw, y: hh}, {x: -hw, y: hh} ];
                    let pts = ptsLocal.map(p => fabric.util.transformPoint(p, matrix));
                    for(let j=0; j<pts.length; j++) {
                        let p1 = pts[j]; let p2 = pts[(j+1)%pts.length];
                        let dist = distToSegment(pointer.x, pointer.y, p1.x, p1.y, p2.x, p2.y);
                        if (dist < minDist) { minDist = dist; closestPoint = closestPointOnSegment(pointer.x, pointer.y, p1.x, p1.y, p2.x, p2.y); }
                    }
                }
            }
            return closestPoint;
        }

        canvas.on('mouse:down', o => {"""

if "calculateBoundarySnap" not in content:
    content = content.replace("canvas.on('mouse:down', o => {", func_code)

# 2. Patch mouse:down
old_md = """            if (isLineShape && activeTool === 'shape') {
                floatingTooltip.style.display = 'block';
                if (!multiClickDrawing) {"""
new_md = """            if (isLineShape && activeTool === 'shape') {
                floatingTooltip.style.display = 'block';

                let snapPt = null;
                if (!o.e.altKey) {
                    snapPt = calculateBoundarySnap(pointer, canvas, null);
                    if (snapPt) { pointer.x = snapPt.x; pointer.y = snapPt.y; }
                }

                if (!multiClickDrawing) {"""
content = content.replace(old_md, new_md)

# 3. Patch mouse:move multiClickDrawing
old_mm1 = """            if (multiClickDrawing) {
                floatingTooltip.style.left = o.e.clientX + 'px';
                floatingTooltip.style.top = o.e.clientY + 'px';

                let snapX = pointer.x; let snapY = pointer.y;
                if (clickPoints.length > 2) {"""
new_mm1 = """            if (multiClickDrawing) {
                floatingTooltip.style.left = o.e.clientX + 'px';
                floatingTooltip.style.top = o.e.clientY + 'px';

                let snapX = pointer.x; let snapY = pointer.y;
                let snapPt = null;
                if (!o.e.altKey) {
                    snapPt = calculateBoundarySnap({x: snapX, y: snapY}, canvas, currentShape);
                    if (snapPt) { snapX = snapPt.x; snapY = snapPt.y; }
                }
                updateSnapMarker(canvas, snapPt);

                if (!snapPt && clickPoints.length > 2) {"""
content = content.replace(old_mm1, new_mm1)

# 4. Patch mouse:move isNormalLine
old_mm2 = """                else if (isNormalLine) {
                    // 일반 화살표도 곡선/다중 클릭과 100% 동일한 알고리즘을 사용하도록 수학적 위치 갱신 도입
                    let angle = Math.atan2(pointer.y - origY, pointer.x - origX);
                    const weight = parseInt(document.getElementById('shape_weight').value);
                    const sizeMult = sysArrowSize === 'xs' ? 1.5 : sysArrowSize === 's' ? 2 : sysArrowSize === 'l' ? 4 : 3;
                    const w = weight * sizeMult + 8;
                    let pullBack = (shapeType === 'arrow') ? ((sysArrowType === 'stealth') ? w * 0.6 : (sysArrowType === 'open') ? 0 : w) : 0;

                    let endX = pointer.x - Math.cos(angle) * pullBack;
                    let endY = pointer.y - Math.sin(angle) * pullBack;

                    let pathStr = `M ${origX} ${origY} L ${endX} ${endY}`;
                    const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                    const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                    canvas.remove(currentShape);
                    currentShape = new fabric.Path(pathStr, { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineCap: 'round', strokeLineJoin: 'round', isTemp: true, isArrowBody: true });
                    canvas.add(currentShape);

                    if (shapeType === 'arrow' && arrowHead) {
                        canvas.remove(arrowHead);
                        arrowHead = createArrowHead(pointer.x, pointer.y, angle, sysArrowType, sysArrowSize, strokeColor, weight);
                        canvas.add(arrowHead);
                    }
                }"""
new_mm2 = """                else if (isNormalLine) {
                    // 일반 화살표도 곡선/다중 클릭과 100% 동일한 알고리즘을 사용하도록 수학적 위치 갱신 도입
                    let snapX = pointer.x; let snapY = pointer.y;
                    let snapPt = null;
                    if (!o.e.altKey) {
                        snapPt = calculateBoundarySnap({x: snapX, y: snapY}, canvas, currentShape);
                        if (snapPt) { snapX = snapPt.x; snapY = snapPt.y; }
                    }
                    updateSnapMarker(canvas, snapPt);

                    let angle = Math.atan2(snapY - origY, snapX - origX);
                    const weight = parseInt(document.getElementById('shape_weight').value);
                    const sizeMult = sysArrowSize === 'xs' ? 1.5 : sysArrowSize === 's' ? 2 : sysArrowSize === 'l' ? 4 : 3;
                    const w = weight * sizeMult + 8;
                    let pullBack = (shapeType === 'arrow') ? ((sysArrowType === 'stealth') ? w * 0.6 : (sysArrowType === 'open') ? 0 : w) : 0;

                    let endX = snapX - Math.cos(angle) * pullBack;
                    let endY = snapY - Math.sin(angle) * pullBack;

                    let pathStr = `M ${origX} ${origY} L ${endX} ${endY}`;
                    const isDashed = document.getElementById('chk_dashed') && document.getElementById('chk_dashed').checked;
                    const dashArr = isDashed ? [weight * 3, weight * 3] : null;

                    canvas.remove(currentShape);
                    currentShape = new fabric.Path(pathStr, { fill: 'transparent', stroke: strokeColor, strokeWidth: weight, strokeDashArray: dashArr, selectable: false, strokeLineCap: 'round', strokeLineJoin: 'round', isTemp: true, isArrowBody: true });
                    canvas.add(currentShape);

                    if (shapeType === 'arrow' && arrowHead) {
                        canvas.remove(arrowHead);
                        arrowHead = createArrowHead(snapX, snapY, angle, sysArrowType, sysArrowSize, strokeColor, weight);
                        canvas.add(arrowHead);
                    }
                }"""
content = content.replace(old_mm2, new_mm2)

# 5. Patch mouse:up
old_mu = """        canvas.on('mouse:up', async o => {
            if (o.target) {"""
new_mu = """        canvas.on('mouse:up', async o => {
            updateSnapMarker(canvas, null);
            if (o.target) {"""
content = content.replace(old_mu, new_mu)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patch applied to index.html!")
