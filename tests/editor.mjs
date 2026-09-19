import puppeteer from 'puppeteer';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const browser = await puppeteer.launch({ headless: true, timeout: 20000 });
try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 1000 });
    const errors = [], remote = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.setRequestInterception(true);
    page.on('request', r => {
        if (/^https?:/.test(r.url())) { remote.push(r.url()); r.abort(); }
        else r.continue();
    });
    await page.goto(pathToFileURL(path.resolve('index.html')).href);
    await page.addScriptTag({ content: await readFile('tests/editor-scenarios.js', 'utf8') });
    const results = await page.evaluate(() => runEditorTests());
    results.push({ name: 'no runtime JavaScript errors', ok: !errors.length, errors });
    results.push({ name: 'zero remote requests', ok: !remote.length, remote });
    await mkdir('test-results', { recursive: true });
    await page.evaluate(async () => {
        isHistoryAction = true; canvas.clear();
        commitLoadToCanvas(null, 1000, 650, '#e4eef8');
        canvas.add(new fabric.Text('Capcraft 1.2 · Popout quality', {left:50,top:40,fontSize:28,fill:'#24354a'}));
        const sample=document.createElement('canvas'); sample.width=270; sample.height=160;
        const c=sample.getContext('2d'); c.fillStyle='#fff';c.fillRect(0,0,270,160);
        c.fillStyle='#333';c.font='16px sans-serif';c.fillText('Capture text 0123456789',15,35);
        c.font='14px sans-serif';c.fillText('원본 유지 / 선명도 조절',15,65);
        c.fillStyle='#888';c.fillText('Gray text and thin edges',15,95);
        c.fillStyle='#1984bf';c.fillRect(15,115,80,22);c.fillStyle='#e7594f';c.fillRect(110,115,80,22);
        const pic=await new Promise(r=>fabric.Image.fromURL(sample.toDataURL(),r)); pic.set({left:65,top:165});canvas.add(pic);
        const mask=new fabric.Rect({left:65,top:165,width:270,height:160,fill:'transparent',stroke:'#267cba',strokeWidth:1});
        canvas.add(mask);createPopoutFromObject(mask);
        for(let i=0;i<100&&!canvas.getObjects().some(o=>o.isPopout);i++) await new Promise(r=>setTimeout(r,20));
        const pop=canvas.getObjects().find(o=>o.isPopout);
        pop.set({left:665,top:330,scaleX:1.7,scaleY:1.7,angle:0,tiltX:12,tiltY:-15});
        pop._baseLeft=665;pop._baseTop=330;applyPopoutTilt(pop);updatePopoutLine(pop);
        canvas.discardActiveObject();canvas.renderAll();
    });
    await page.screenshot({ path: 'test-results/editor.png' });
    await writeFile('test-results/editor.json', JSON.stringify(results, null, 2));
    for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'} ${r.name}${r.error ? ': ' + r.error : ''}`);
    if (errors.length) console.log(errors);
    if (results.some(r => !r.ok)) process.exitCode = 1;
} finally { await browser.close(); }
