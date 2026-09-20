// Actual installed Chrome, disposable profile, no personal capture history.
import puppeteer from 'puppeteer';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';

const smoke=process.argv.includes('--smoke');
const browser=await puppeteer.launch({
 executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',
 headless:smoke,defaultViewport:null,args:['--window-size=1463,900'],timeout:20000
});
try {
 const page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>{errors.push(String(e));console.error(e);});
 await page.goto(pathToFileURL(path.resolve('index.html')).href);
 await page.addScriptTag({content:await readFile('tests/rendering-scene.js','utf8')});
 await page.addScriptTag({content:await readFile('tests/comparison-scene.js','utf8')});
 await page.evaluate(()=>prepareComparisonScene());
 console.log(await browser.version());
 console.log(await page.evaluate(()=>({viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,
     objects:canvas.getObjects().length,thumbnails:recentList.length})));
 if(errors.length)throw Error('Comparison page has JavaScript errors');
 console.log('READY: drag/resize objects; close this test Chrome window when done.');
 if(!smoke)await new Promise(resolve=>browser.once('disconnected',resolve));
} finally {if(browser.connected)await browser.close();}
