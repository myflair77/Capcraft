import os

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Patch mouse:down for pen
old_pen_down = """            if (activeTool === 'pen' && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                isDrawing = true; origX = pointer.x; origY = pointer.y;
                const weight = parseInt(document.getElementById('pen_weight').value) || 5;"""
new_pen_down = """            if (activeTool === 'pen' && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                let snapPt = null;
                if (!o.e.altKey) {
                    snapPt = calculateBoundarySnap(pointer, canvas, null);
                    if (snapPt) { pointer.x = snapPt.x; pointer.y = snapPt.y; }
                }

                isDrawing = true; origX = pointer.x; origY = pointer.y;
                const weight = parseInt(document.getElementById('pen_weight').value) || 5;"""
content = content.replace(old_pen_down, new_pen_down)

# 2. Patch mouse:move for pen
old_pen_move = """            if (activeTool === 'pen' && isDrawing && currentShape && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                let endX = pointer.x; let endY = pointer.y;

                let angleDeg = Math.atan2(endY - origY, endX - origX) * 180 / Math.PI;
                let normAngle = (angleDeg + 360) % 360;

                const snapTolerance = 2;
                if (Math.abs(normAngle - 0) <= snapTolerance || Math.abs(normAngle - 360) <= snapTolerance) { endY = origY; }
                else if (Math.abs(normAngle - 90) <= snapTolerance) { endX = origX; }
                else if (Math.abs(normAngle - 180) <= snapTolerance) { endY = origY; }
                else if (Math.abs(normAngle - 270) <= snapTolerance) { endX = origX; }

                const weight = parseInt(document.getElementById('pen_weight').value) || 5;"""

new_pen_move = """            if (activeTool === 'pen' && isDrawing && currentShape && document.querySelector('input[name="pen_mode"]:checked').value === 'straight') {
                let snapPt = null;
                let snapX = pointer.x; let snapY = pointer.y;
                if (!o.e.altKey) {
                    snapPt = calculateBoundarySnap({x: snapX, y: snapY}, canvas, currentShape);
                    if (snapPt) { snapX = snapPt.x; snapY = snapPt.y; }
                }
                updateSnapMarker(canvas, snapPt);

                let endX = snapX; let endY = snapY;

                let angleDeg = Math.atan2(endY - origY, endX - origX) * 180 / Math.PI;
                let normAngle = (angleDeg + 360) % 360;

                const snapTolerance = 2;
                if (!snapPt) {
                    if (Math.abs(normAngle - 0) <= snapTolerance || Math.abs(normAngle - 360) <= snapTolerance) { endY = origY; }
                    else if (Math.abs(normAngle - 90) <= snapTolerance) { endX = origX; }
                    else if (Math.abs(normAngle - 180) <= snapTolerance) { endY = origY; }
                    else if (Math.abs(normAngle - 270) <= snapTolerance) { endX = origX; }
                }

                const weight = parseInt(document.getElementById('pen_weight').value) || 5;"""
content = content.replace(old_pen_move, new_pen_move)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Pen straight patch applied.")
