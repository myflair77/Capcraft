import puppeteer from 'puppeteer';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const browser = await puppeteer.launch({ headless: true, timeout: 20000 });
try {
    const page = await browser.newPage(); await page.setViewport({ width: 1400, height: 1000 });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.resolve('index.html')).href);
    await page.addScriptTag({ content: await readFile('tests/rendering-scene.js', 'utf8') });
    await page.evaluate(() => prepareRenderingScene());
    await page.evaluate(() => {
        window.frameStats = { frames: 0, blank: 0, bottomBlank: 0, bottomBoundaryChanges: 0, missingObjectSamples: 0, maxGap: 0, dimensionsReset: 0, moves: 0, scales: 0 };
        canvas.on('object:moving', () => frameStats.moves++);
        canvas.on('object:scaling', () => frameStats.scales++);
        const original = canvas.setDimensions;
        canvas.setDimensions = function (...args) { frameStats.dimensionsReset++; return original.apply(this, args); };
        let previous, previousBottom;
        function sample(t) {
            const pixel = canvas.contextContainer.getImageData(5, 5, 1, 1).data;
            frameStats.frames++;
            if (pixel[3] !== 255) frameStats.blank++;
            const height=canvas.lowerCanvasEl.height, width=canvas.lowerCanvasEl.width;
            const bottomPixel=canvas.contextContainer.getImageData(Math.floor(width/2),height-2,1,1).data;
            if(bottomPixel[3]!==255)frameStats.bottomBlank++;
            const bottom=canvas.lowerCanvasEl.getBoundingClientRect().bottom;
            if(previousBottom!==undefined && Math.abs(bottom-previousBottom)>.5)frameStats.bottomBoundaryChanges++;
            previousBottom=bottom;
            for (const obj of renderingObjects) {
                const p = fabric.util.transformPoint(obj.getCenterPoint(), canvas.viewportTransform);
                const ratio = canvas.getRetinaScaling();
                const c = canvas.contextContainer.getImageData(Math.round(p.x*ratio), Math.round(p.y*ratio), 1, 1).data;
                if (c[0]===228 && c[1]===238 && c[2]===248) frameStats.missingObjectSamples++;
            }
            if (previous) frameStats.maxGap = Math.max(frameStats.maxGap, t - previous);
            previous = t;
            window.sampleFrame = requestAnimationFrame(sample);
        }
        requestAnimationFrame(sample);
    });
    const outcomes = [];
    const clicks = [];
    await page.evaluate(() => {
        window.visiblePaints=0;
        canvas.on('after:render', e=>{if(e.ctx===canvas.contextContainer) visiblePaints++;});
    });
    for (let i = 0; i < 4; i++) {
        let point = await page.evaluate(i => {
            const obj = renderingObjects[i]; canvas.discardActiveObject();
            const r = canvas.upperCanvasEl.getBoundingClientRect(), p = obj.getCenterPoint();
            return { x: r.left + p.x * currentZoom, y: r.top + p.y * currentZoom,
                left: obj.left, top: obj.top, scaleX: obj.scaleX };
        }, i);
        await page.evaluate(()=>{visiblePaints=0;});
        await page.mouse.click(point.x, point.y);
        clicks.push(await page.evaluate(async i=>{
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            return {type:['shape','emoji','image','mosaic'][i], selected:canvas.getActiveObject()===renderingObjects[i], painted:visiblePaints>0};
        },i));
        await page.mouse.move(point.x, point.y); await page.mouse.down();
        await page.mouse.move(point.x + 60, point.y + 45, { steps: 24 }); await page.mouse.up();
        const corner = await page.evaluate(i => {
            const obj = renderingObjects[i]; obj.setCoords();
            const r = canvas.upperCanvasEl.getBoundingClientRect(), p = obj.oCoords.br;
            return { x: r.left + p.x * currentZoom, y: r.top + p.y * currentZoom };
        }, i);
        await page.mouse.move(corner.x, corner.y); await page.mouse.down();
        await page.mouse.move(corner.x + 70, corner.y + 50, { steps: 24 }); await page.mouse.up();
        outcomes.push(await page.evaluate(({ i, point }) => {
            const obj = renderingObjects[i];
            return { type: ['shape', 'emoji', 'image', 'mosaic'][i], moved: obj.left !== point.left,
                resized: obj.scaleX !== point.scaleX, present: canvas.getObjects().includes(obj) };
        }, { i, point }));
    }
    const stats = await page.evaluate(() => { cancelAnimationFrame(sampleFrame); return frameStats; });
    await mkdir('test-results', { recursive: true });
    await page.screenshot({ path: 'test-results/rendering.png' });
    const result = { outcomes, clicks, stats, errors };
    await writeFile('test-results/rendering.json', JSON.stringify(result, null, 2));
    console.log(result);
    if (errors.length || stats.blank || stats.missingObjectSamples || stats.dimensionsReset || clicks.some(r=>!r.selected||!r.painted) || outcomes.some(r => !r.moved || !r.resized || !r.present)) process.exitCode = 1;
} finally { await browser.close(); }
