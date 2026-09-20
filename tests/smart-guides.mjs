import puppeteer from 'puppeteer';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {mkdir} from 'node:fs/promises';
const browser=await puppeteer.launch({headless:true});
try {
    const page=await browser.newPage();await page.setViewport({width:1800,height:1400});
    await page.goto(pathToFileURL(path.resolve('index.html')).href,{waitUntil:'domcontentloaded'});
    for(const zoom of [.5,1,2]) {
        await page.evaluate(zoom=>{
            activeTool=null;canvas.isDrawingMode=false;isHistoryAction=true;canvas.clear();
            commitLoadToCanvas(null,700,500,'white');
            currentZoom=zoom;panX=0;panY=0;updateCanvasTransform();
            canvas.add(new fabric.Rect({id:'reference',left:400,top:180,width:100,height:70,strokeWidth:0,fill:'#93c5fd'}));
            canvas.add(new fabric.Rect({id:'moving',left:150,top:340,width:80,height:60,strokeWidth:0,fill:'#2563eb'}));
            canvas.renderAll();
        },zoom);
        await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
        const coords=await page.evaluate(()=>{
            canvas.calcOffset();const r=canvas.upperCanvasEl.getBoundingClientRect();
            return {x:r.left+190*r.width/canvas.width,y:r.top+370*r.height/canvas.height,scale:r.width/canvas.width};
        });
        await page.mouse.move(coords.x,coords.y);await page.mouse.down();
        // Stop four screen pixels short of the target edge.
        await page.mouse.move(coords.x+250*coords.scale-4,coords.y,{steps:8});
        let result=await page.evaluate(()=>({left:canvas.getObjects().find(o=>o.id==='moving').left,visible:document.getElementById('smart_alignment_guides').style.display}));
        if(Math.abs(result.left-400)>.01||result.visible!=='block')throw Error(`zoom ${zoom}: ${JSON.stringify(result)}`);
        if(zoom===1){await mkdir('test-results',{recursive:true});await page.screenshot({path:'test-results/smart-guides.png'});}
        await page.keyboard.down('Alt');
        await page.mouse.move(coords.x+250*coords.scale-3,coords.y);
        result=await page.evaluate(()=>({left:canvas.getObjects().find(o=>o.id==='moving').left,visible:document.getElementById('smart_alignment_guides').style.display}));
        if(Math.abs(result.left-400)<.1||result.visible!=='none')throw Error('Alt did not bypass snap');
        await page.mouse.up();await page.keyboard.up('Alt');
        console.log(`PASS actual drag, screen-space snap and Alt at ${zoom}x`);
    }
    await page.goto(pathToFileURL(path.resolve('guide.html')).href,{waitUntil:'domcontentloaded'});
    console.log(await page.evaluate(()=>({guideSections:document.querySelectorAll('.section').length,email:document.querySelector('a[href^="mailto"]').getAttribute('href'),smartGuide:document.body.innerText.includes('스마트 정렬 가이드선')})));
} finally {await browser.close();}
