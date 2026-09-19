import puppeteer from 'puppeteer';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {mkdir} from 'node:fs/promises';
const browser=await puppeteer.launch({headless:true});
try {
    const page=await browser.newPage();await page.setViewport({width:1100,height:800});
    await page.goto(pathToFileURL(path.resolve('index.html')).href,{waitUntil:'domcontentloaded'});
    console.log(await page.evaluate(()=>{
        const check=(ok,msg)=>{if(!ok)throw new Error(msg);};
        commitLoadToCanvas(null,700,460,'white');isHistoryAction=true;
        const ids=[...document.querySelectorAll('#panel_pen input[type=checkbox]')].map(el=>el.id);
        check(ids.indexOf('pen_dashed')<ids.indexOf('pen_wave')&&ids.indexOf('pen_wave')<ids.indexOf('pen_arrow'),'option order');
        for(const kind of [null,'pencil','brush','charcoal']) {
            canvas.clear();
            const obj=new fabric.Path('M 100 100 Q 180 140 260 100 L 320 150',{stroke:'#333',strokeWidth:5,fill:null,naturalPen:kind});
            canvas.add(obj);canvas.setActiveObject(obj);
            const center=obj.getCenterPoint(),source=JSON.stringify(obj.path);
            for(let mask=0;mask<8;mask++) {
                ['pen_dashed','pen_wave','pen_arrow'].forEach((id,i)=>{
                    const el=document.getElementById(id);el.checked=!!(mask&(1<<i));el.dispatchEvent(new Event('change'));
                });
                for(const width of [2,18,5]) {
                    const input=document.getElementById('pen_weight');input.value=width;input.dispatchEvent(new Event('input'));
                    check(obj.strokeWidth===width,'width');
                    check(!!obj.strokeDashArray?.length===!!(mask&1),'dash toggle');
                    check(!!obj.waveLine===!!(mask&2),'wave toggle');
                    check(!!obj.penArrow===!!(mask&4),'arrow toggle');
                    if(mask&1)check(JSON.stringify(obj.strokeDashArray)===JSON.stringify(StrokeEffects.dash(width)),'dash width refresh');
                    check(obj.getCenterPoint().distanceFrom(center)<.001,'effect changed position');
                    check(JSON.stringify(obj.path)===source,'source path changed');
                    canvas.renderAll();check(!/NaN/.test(obj.toSVG()),'invalid export');
                }
            }
            obj.set({scaleX:1.6,scaleY:1.6,waveLine:true});normalizeScale(obj);
            check(JSON.stringify(obj.path)===source,'resize destroyed wave source');
            const saved=obj.toObject();check(saved.waveLine&&saved.penArrow,'effects not serialized');
        }
        canvas.clear();return 'PASS: pen effect combinations, width updates, stable position, resize and serialization';
    }));
    const results=await page.evaluate(()=>{
        commitLoadToCanvas(null,700,460,'white');isHistoryAction=true;canvas.clear();canvas.setViewportTransform([1,0,0,1,0,0]);canvas.setDimensions({width:700,height:460});canvas.backgroundColor='white';
        const results=[];
        for(const [i,kind] of ['pencil','brush','charcoal'].entries()) {
            const label=new fabric.Text(kind,{left:25,top:35+i*135,fontSize:20,fill:'#333'});canvas.add(label);
            const brush=new NaturalPens.Brush(canvas);brush.kind=kind;brush.width=kind==='pencil'?6:26;brush.color='#333';
            const points=Array.from({length:180},(_,j)=>new fabric.Point(145+j*2.5,65+i*135+Math.sin(j/13)*20));
            const path=brush.createPath(brush.convertPointsToSVGPath(points));canvas.add(path);
            const t=performance.now();for(let n=0;n<100;n++)canvas.renderAll();
            results.push({kind,cachedRenderMs:(performance.now()-t)/100});
            const start=performance.now();const d=NaturalPens.geometry(Array.from({length:5000},(_,j)=>({x:j*2,y:Math.sin(j/15)*30})),kind,26,false);
            results.push({kind,longGeometryMs:performance.now()-start,bytes:d.length});
        }
        canvas.renderAll();return results;
    });
    await mkdir('test-results',{recursive:true});
    await page.screenshot({path:'test-results/natural-pens.png'});
    await page.evaluate(()=>{document.getElementById('btn_tool_pen').click();document.getElementById('pen_arrow').checked=true;});
    await page.screenshot({path:'test-results/pen-toolbar.png'});
    await page.evaluate(()=>openModal('modal_settings'));
    await page.evaluate(()=>document.getElementById('set_pen_brush_weight').scrollIntoView({block:'center'}));
    await page.screenshot({path:'test-results/pen-settings.png'});
    await page.evaluate(()=>{
        closeModals();canvas.clear();canvas.backgroundColor='white';isHistoryAction=true;
        document.getElementById('pen_arrow').checked=true;
        ['triangle','stealth','open'].forEach((type,i)=>{
            document.getElementById('set_arrow_type').value=type;
            const y=40+i*135;
            const obj=new fabric.Path(`M 100 ${y} C 160 ${y} 300 ${y+20} 370 ${y+75}`,{stroke:'#2868ec',strokeWidth:7,fill:'transparent'});
            applyPenArrow(obj);canvas.add(obj);
            canvas.add(new fabric.Text(type,{left:430,top:y+40,fontSize:18,fill:'#333'}));
        });canvas.renderAll();
    });
    await page.screenshot({path:'test-results/pen-arrow-alignment.png'});
    await page.evaluate(()=>{
        canvas.clear();canvas.backgroundColor='white';isHistoryAction=true;activeTool=null;
        ShapePens.kinds.forEach((kind,i)=>{
            const obj=new fabric.Rect({left:25+i*135,top:65,width:95,height:85,stroke:'#334455',strokeWidth:8,fill:'#fce6c9'});
            ShapePens.apply(obj,kind,kind==='highlighter'?30:100);canvas.add(obj);
            const ellipse=new fabric.Ellipse({left:25+i*135,top:230,rx:47,ry:40,stroke:'#334455',strokeWidth:8,fill:'#fce6c9'});
            ShapePens.apply(ellipse,kind,kind==='highlighter'?30:100);canvas.add(ellipse);
            canvas.add(new fabric.Text(kind,{left:25+i*135,top:180,fontSize:17,fill:'#333'}));
        });
        canvas.renderAll();document.getElementById('btn_tool_shape').click();updateWorkspaceInset();
    });
    await page.screenshot({path:'test-results/shape-pens.png'});
    console.log(await page.evaluate(()=>({toolbar:document.getElementById('sub_toolbar').getBoundingClientRect().toJSON(),workspace:workspace.getBoundingClientRect().toJSON(),left:document.getElementById('sub_toolbar').style.left})));
    console.log(JSON.stringify(results,null,2));
}finally{await browser.close();}
