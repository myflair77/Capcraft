import puppeteer from 'puppeteer';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { writeFile, mkdir } from 'node:fs/promises';
const browser = await puppeteer.launch({headless:true});
try {
    const page=await browser.newPage();
    await page.goto(pathToFileURL(path.resolve('index.html')).href);
    const result=await page.evaluate(async()=>{
        commitLoadToCanvas(null,1600,1000,'#eeeeee');
        const mask=new fabric.Rect({left:100,top:100,width:640,height:360,fill:'transparent',strokeWidth:0});
        canvas.add(new fabric.Text('Performance sample 한글 ABC 0123456789',{left:120,top:150,fontSize:32}),mask);
        const start=performance.now(); createPopoutFromObject(mask);
        while(!canvas.getObjects().some(o=>o.isPopout)) await new Promise(r=>setTimeout(r,10));
        const creationMs=performance.now()-start, pop=canvas.getObjects().find(o=>o.isPopout);
        const measure=fn=>{const t=performance.now();fn();return performance.now()-t;};
        const regenerations=[],history=[];
        for(let i=0;i<5;i++) {
            pop.left+=1;pop._baseLeft+=1;
            regenerations.push(measure(()=>regeneratePopoutBase(pop)));
            history.push(measure(()=>saveHistory()));
        }
        return {creationMs,regenerations,history,sourcePixels:pop._croppedBg.width*pop._croppedBg.height,rasterPixels:pop._element.width*pop._element.height};
    });
    await mkdir('test-results',{recursive:true});
    await writeFile(`test-results/performance-${process.argv[2]||'current'}.json`,JSON.stringify(result,null,2));
    console.log(result);
} finally {await browser.close();}
