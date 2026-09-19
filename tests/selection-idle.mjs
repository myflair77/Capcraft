import puppeteer from 'puppeteer';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const browser = await puppeteer.launch({headless:true});
try {
    const page = await browser.newPage();
    await page.setViewport({width:1400,height:1000});
    await page.goto(pathToFileURL(path.resolve('index.html')).href);
    await page.addScriptTag({content:await readFile('tests/selection-scene.js','utf8')});
    await page.evaluate(() => prepareSelectionScene());
    await page.addScriptTag({content:await readFile('tests/selection-trace.js','utf8')});
    await page.evaluate(() => installSelectionTrace());
    const outcomes=[];
    for(let i=0;i<30;i++) {
        const target=`selection-${i%5+1}`;
        const point=await page.evaluate(id=>{
            const obj=canvas.getObjects().find(o=>o.id===id);
            const p=fabric.util.transformPoint(obj.getCenterPoint(),canvas.viewportTransform);
            const r=canvas.upperCanvasEl.getBoundingClientRect();
            return {x:r.left+p.x*r.width/canvas.width,y:r.top+p.y*r.height/canvas.height};
        },target);
        await page.mouse.click(point.x,point.y);
        await new Promise(r=>setTimeout(r,[20,100,400,1000][i%4]));
        const state=await page.evaluate(()=>({selected:canvas.getActiveObject()?.id,trace:selectionTrace.slice(-8)}));
        outcomes.push({target,...state});
    }
    await mkdir('test-results',{recursive:true});
    await writeFile('test-results/selection-idle.json',JSON.stringify(outcomes,null,2));
    const failures=outcomes.filter(o=>o.target!==o.selected);
    console.log(JSON.stringify({clicks:outcomes.length,failures}));
    if(failures.length) process.exitCode=1;
} finally {await browser.close();}
