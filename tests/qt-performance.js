window.runQtPerformance = async function () {
    await prepareRenderingScene();
    const samples = [];
    for (let i = 0; i < 60; i++) {
        const obj = renderingObjects[i % renderingObjects.length];
        const start = performance.now();
        obj.set({left:obj.left + (i%2 ? -1 : 1)});
        obj.setCoords();
        canvas.setActiveObject(obj);
        canvas.renderAll();
        samples.push(performance.now()-start);
        await new Promise(resolve=>setTimeout(resolve,16));
    }
    samples.sort((a,b)=>a-b);
    return [{name:'Qt move/select render timings (CPU work, not screen latency)',ok:true,
        medianMs:samples[30],p95Ms:samples[57],maxMs:samples[59]}];
};
