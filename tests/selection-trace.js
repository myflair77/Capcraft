// Diagnostic only: do not request frames or alter selection while observing it.
window.installSelectionTrace = function () {
    let sequence = 0;
    const ids = new WeakMap();
    let nextId = 0;
    const id = obj => {
        if (!obj) return null;
        if (!ids.has(obj)) ids.set(obj, ++nextId);
        return `${obj.type}:${ids.get(obj)}`;
    };
    window.selectionTrace = [];
    const record = (phase, target) => {
        const row = { sequence, phase, target: id(target), active: id(canvas.getActiveObject()) };
        selectionTrace.push(row);
        if (selectionTrace.length > 2000) selectionTrace.shift();
        console.log('SELECTION_TRACE ' + JSON.stringify(row));
    };
    canvas.on('mouse:down:before', e => { sequence++; record('down-before', e.target); });
    for (const phase of ['mouse:down', 'mouse:up:before', 'mouse:up', 'selection:created', 'selection:updated', 'selection:cleared']) {
        canvas.on(phase, e => record(phase, e.target));
    }
    const drawControls = canvas.drawControls;
    canvas.drawControls = function (ctx) {
        if (ctx === canvas.contextContainer) record('draw-controls', this.getActiveObject());
        return drawControls.apply(this, arguments);
    };
    canvas.on('after:render', e => {
        if (e.ctx === canvas.contextContainer) record('visible-canvas-render', canvas.getActiveObject());
    });
};
