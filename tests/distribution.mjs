import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import puppeteer from 'puppeteer';
const root=path.resolve('distribution');
const server=http.createServer(async(req,res)=>{
  const file=path.resolve(root,'.'+(req.url==='/'?'/index.html':req.url.split('?')[0]));
  if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  try{const bytes=await fs.readFile(file);res.setHeader('Content-Type',({'.css':'text/css','.js':'text/javascript','.json':'application/json','.html':'text/html'})[path.extname(file)]||'text/plain');res.end(bytes);}catch{res.writeHead(404).end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await puppeteer.launch({headless:true});
try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await fs.mkdir('test-results',{recursive:true});
  for(const width of [1365,390]){
    await page.setViewport({width,height:900});
    for(const route of ['', 'privacy.html', 'signing.html']) {
      const response=await page.goto(`http://127.0.0.1:${server.address().port}/${route}`,{waitUntil:'networkidle0'});
      if(response.status()!==200)throw Error(`Missing page: ${route}`);
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error(`Horizontal overflow: ${route}`);
      if(!route) {
        for(const link of ['privacy.html','signing.html']) {
          if(!await page.$(`a[href="${link}"]`))throw Error(`Missing policy link: ${link}`);
        }
      }
      if(route==='signing.html' && !await page.evaluate(()=>document.body.textContent.includes('Current Capcraft 1.2 downloads are unsigned')))throw Error('Missing unsigned disclosure');
      await page.screenshot({path:`test-results/distribution-${route || 'home'}-${width}.png`,fullPage:true});
    }
  }
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS distribution desktop/mobile layout and JavaScript');
}finally{await browser.close();server.close();}
