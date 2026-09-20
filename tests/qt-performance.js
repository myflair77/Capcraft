window.runQtPerformance = async function () {
    await prepareRenderingScene();
    const samples = [];
    const gaps = []; let previous=performance.now();
    // The old benchmark never sent pointerdown, so drag-only workarounds were
    // not measured. Explicitly exercise the gesture lifecycle in this variant.
    if(window.benchmarkReadbackGesture) canvas.upperCanvasEl.dispatchEvent(new PointerEvent('pointerdown',{
        bubbles:true,button:0,pointerId:77,isPrimary:true,clientX:0,clientY:0}));
    for (let i = 0; i < 60; i++) {
        const obj = renderingObjects[i % renderingObjects.length];
        const start = performance.now();
        obj.set({left:obj.left + (i%2 ? -1 : 1)});
        obj.setCoords();
        canvas.setActiveObject(obj);
        canvas.renderAll();
        samples.push(performance.now()-start);
        await new Promise(resolve=>setTimeout(resolve,16));
        const now=performance.now();gaps.push(now-previous);previous=now;
    }
    if(window.benchmarkReadbackGesture) document.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:77}));
    samples.sort((a,b)=>a-b);
    return [{name:'Qt move/select render timings (CPU work, not screen latency)',ok:true,
        medianMs:samples[30],p95Ms:samples[57],maxMs:samples[59],
        maxLoopGapMs:Math.max(...gaps),gesture:!!window.benchmarkReadbackGesture,
        readback:window.capcraftPresentationStats?{...window.capcraftPresentationStats}:null}];
};
