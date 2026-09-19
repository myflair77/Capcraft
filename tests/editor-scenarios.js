window.runEditorTests = async function () {
    const results = [];
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const check = (condition, message) => { if (!condition) throw new Error(message); };
    const near = (a, b) => Math.abs(a - b) < 0.05;
    async function until(predicate) {
        for (let i = 0; i < 100; i++) { if (predicate()) return; await wait(20); }
        throw new Error('Timed out waiting for editor state');
    }
    async function test(name, fn) {
        try { await reset(); await fn(); results.push({ name, ok: true }); }
        catch (error) { results.push({ name, ok: false, error: error.message }); }
    }
    async function reset() {
        const active = canvas.getActiveObject();
        if (active?.isEditing) active.exitEditing();
        activeTool = null; canvas.isDrawingMode = false;
        document.querySelectorAll('.btn-tool.group-edit.active').forEach(b => b.classList.remove('active'));
        isHistoryAction = true; canvas.discardActiveObject(); canvas.clear();
        recentList = []; activeRecentIdx = -1; stateHistory = []; historyIndex = -1;
        commitLoadToCanvas(null, 800, 600, '#f0e0d0');
        await until(() => hasActiveCanvas && !isHistoryAction);
    }
    function line(arrow = false, type = 'polyline') {
        const points = [{ x: 120, y: 160 }, { x: 240, y: 230 }, { x: 360, y: 150 }];
        const seed = { __capcraftLineType: type, stroke: '#ff0000', strokeWidth: 5,
            arrowType: arrow ? 'triangle' : null, arrowSize: 'm', isArrowGroup: arrow };
        const obj = createLineShapeFromPoints(seed, points);
        obj.__capcraftPoints = points; obj.__capcraftLineType = type;
        canvas.add(obj); canvas.setActiveObject(obj); makeLineControls(obj);
        return obj;
    }
    await test('palette color restores transparent shape and pen backgrounds without moving them', async () => {
        for (const kind of ['rect', 'pen']) {
            const obj = kind === 'rect'
                ? new fabric.Rect({left:170,top:140,width:100,height:80,fill:'transparent',stroke:'black'})
                : new fabric.Path('M 0 0 L 100 0 L 100 80 Z',{left:170,top:140,fill:'transparent',stroke:'black'});
            canvas.add(obj);canvas.setActiveObject(obj);
            const input=document.getElementById(kind==='rect'?'shape_bg_opacity_input':'pen_bg_opacity_input');
            input.value=100;
            targetColorBtn=kind==='rect'?'fill':'btn_pen_bg';
            const left=obj.left,top=obj.top;
            document.querySelector('.palette-cell[data-name="검정"]').click();
            check(new fabric.Color(obj.fill).getAlpha()>0,kind+' remains transparent');
            check(near(obj.left,left)&&near(obj.top,top),kind+' moved on fill change');
            input.value=40;
            document.querySelector('.palette-cell[data-name="하양"]').click();
            check(near(new fabric.Color(obj.fill).getAlpha(),0.6),'Partial transparency lost');
            document.querySelector('.palette-cell[data-name="투명"]').click();
            check(new fabric.Color(obj.fill).getAlpha()===0,'Transparent choice no longer works');
        }
    });
    await test('arrow property dialog supports head styles, five sizes and endpoint reversal', async () => {
        for (const lineType of ['normal','polyline','curve']) {
            let obj=line(true,lineType);
            const original=obj.__capcraftPoints.map(p=>({...p}));
            const id=obj.id='arrow-dialog-'+lineType;
            let previousWidth=0;
            for (const size of ['xs','s','m','l','xl']) {
                canvas.fire('mouse:dblclick',{target:obj,e:{}});
                check(document.getElementById('edit_arrow_options').style.display==='block','Arrow options hidden');
                document.getElementById('edit_arrow_size').value=size;
                document.getElementById('edit_arrow_type').value='triangle';
                applyObjectEdit();obj=canvas.getActiveObject();
                check(obj.arrowSize===size && obj.id===id,'Properties or identity lost');
                check(JSON.stringify(obj.__capcraftPoints)===JSON.stringify(original),'Endpoints drifted');
                const head=obj.getObjects().find(o=>o.isArrowHead);
                check(head.width>previousWidth,'Size did not increase');previousWidth=head.width;
            }
            for (const style of ['stealth','open','triangle']) {
                canvas.fire('mouse:dblclick',{target:obj,e:{}});
                document.getElementById('edit_arrow_type').value=style;
                document.getElementById('edit_arrow_reverse').checked=true;
                const before=obj.__capcraftPoints.map(p=>({...p}));
                applyObjectEdit();obj=canvas.getActiveObject();
                check(obj.arrowType===style,'Wrong head style');
                check(JSON.stringify(obj.__capcraftPoints)===JSON.stringify(before.reverse()),'Direction was not reversed');
                check(obj.getObjects().filter(o=>o.isArrowHead).length===1,'Duplicate arrow head');
                canvas.fire('mouse:dblclick',{target:obj,e:{}});
                check(!document.getElementById('edit_arrow_reverse').checked,'Reverse checkbox not reset');
                closeModals();
            }
        }
    });
    await test('arrow reversal preserves endpoint attachments and serialized settings', async () => {
        const a=new fabric.Rect({left:0,top:50,width:100,height:100,fill:'red',id:'source'});
        const b=new fabric.Rect({left:400,top:50,width:100,height:100,fill:'blue',id:'destination'});
        canvas.add(a,b);
        const points=[{x:100,y:100},{x:400,y:100}];
        let obj=createLineShapeFromPoints({__capcraftLineType:'normal',arrowType:'triangle',arrowSize:'m',stroke:'black',strokeWidth:4},points,a,b);
        obj.__capcraftPoints=points;obj.__capcraftLineType='normal';canvas.add(obj);canvas.setActiveObject(obj);
        canvas.fire('mouse:dblclick',{target:obj,e:{}});
        document.getElementById('edit_arrow_reverse').checked=true;
        document.getElementById('edit_arrow_size').value='xl';
        applyObjectEdit();obj=canvas.getActiveObject();
        check(obj.startLinkedObj===b&&obj.endLinkedObj===a,'Endpoint links not swapped');
        syncAllLineLinkedIds();
        check(obj.startLinkedObjId==='destination'&&obj.endLinkedObjId==='source','Saved links incorrect');
        check(obj.toObject().arrowSize==='xl','XL size not serialized');
        a.set({top:180});a.setCoords();
        updateLinkedLinesOnTransform(a);
        check(obj.endLinkedObj===a&&obj.__capcraftPoints.at(-1).y>=180,'Reversed endpoint no longer follows target');
    });
    await test('natural pens draw distinct stable textures, restore and export as single objects', async () => {
        const samples=[];
        for (const kind of ['pencil','brush','charcoal']) {
            activeTool='pen';
            const input=document.getElementById('pen_type');input.value=kind;input.dispatchEvent(new Event('change'));
            check(canvas.freeDrawingBrush.type==='natural'&&canvas.freeDrawingBrush.kind===kind,'Wrong brush');
            check(document.getElementById('pen_highlighter_intensity_input').style.display==='none','Highlighter UI leaked');
            const brush=canvas.freeDrawingBrush;
            brush.onMouseDown({x:80,y:100},{e:{isPrimary:true}});
            for(let i=1;i<=40;i++)brush.onMouseMove({x:80+i*7,y:100+Math.sin(i/6)*30},{e:{isPrimary:true}});
            brush.onMouseUp({e:{isPrimary:true}});
            const obj=canvas.getObjects().findLast(o=>o.naturalPen===kind);
            check(obj&&obj.type==='path','Stroke was not finalized');
            canvas.renderAll();
            const first=obj.toDataURL();canvas.renderAll();check(first===obj.toDataURL(),'Texture changes on redraw');
            samples.push(first);
            const restored=await new Promise(resolve=>fabric.util.enlivenObjects([obj.toObject()],items=>resolve(items[0])));
            check(restored.naturalPen===kind&&restored.toDataURL()===first,'Saved texture lost');
            check(restored.toSVG().includes('stroke:none;fill:'),'Vector texture missing in SVG');
            obj.set({stroke:'#2868ec',strokeWidth:30});canvas.renderAll();check(obj.toDataURL()!==first,'Color/width edit ignored');
            obj.set({scaleX:1.5,scaleY:1.2});normalizeScale(obj);check(obj.naturalPen===kind,'Resize lost texture');
        }
        check(new Set(samples).size===3,'Textures are identical');
        check(canvas.getObjects().filter(o=>o.naturalPen).length===3,'Particles became separate objects');
        activeTool='pen';document.getElementById('pen_type').value='ballpoint';updatePenBrush();
        check(canvas.freeDrawingBrush.type!=='natural','Natural brush leaked into ballpoint');
    });
    await test('linked endpoints keep local anchors during moves, rotation, scaling and restore', async () => {
        for(const arrow of [false,true]) {
            const a=new fabric.Rect({left:50,top:50,width:100,height:100,fill:'red'});
            const b=new fabric.Rect({left:450,top:50,width:100,height:100,fill:'blue'});canvas.add(a,b);
            const points=[{x:150,y:75},{x:450,y:130}];
            const obj=createLineShapeFromPoints({__capcraftLineType:'normal',arrowType:arrow?'triangle':null,arrowSize:'m',stroke:'black',strokeWidth:4},points,a,b);
            obj.__capcraftPoints=points;obj.__capcraftLineType='normal';canvas.add(obj);
            const anchor={...obj.startAnchor},end={...obj.endAnchor};
            for(const change of [{left:400,top:260},{angle:75},{scaleX:1.8,scaleY:.7},{width:180,height:120}]) {
                a.set(change);a.setCoords();updateLinkedLinesOnTransform(a);
                const expected=LineAnchors.point(a,anchor),actual=obj.__capcraftPoints[0];
                check(near(expected.x,actual.x)&&near(expected.y,actual.y),'Attachment slid on target');
                check(near(obj.endAnchor.x,end.x)&&near(obj.endAnchor.y,end.y),'Other endpoint changed');
            }
            syncAllLineLinkedIds();
            const revived=await new Promise(r=>fabric.util.enlivenObjects([obj.toObject(['__capcraftPoints','__capcraftLineType','startLinkedObjId','endLinkedObjId'])],items=>r(items[0])));
            check(near(revived.startAnchor.x,anchor.x)&&near(revived.startAnchor.y,anchor.y),'Anchor lost in JSON');
            // Manual endpoint relocation records a new local anchor.
            const manual=LineAnchors.point(a,{x:-.5,y:0});
            obj.startAnchor=LineAnchors.capture(a,manual);obj.__capcraftPoints[0]=manual;
            a.set({left:100});a.setCoords();updateLinkedLinesOnTransform(a);
            check(near(obj.startAnchor.x,-.5)&&near(obj.startAnchor.y,0),'Manual anchor not retained');
        }
    });
    await test('pen dropdown controls, profiles and arrow endpoints work for all five pens', async () => {
        const group=document.getElementById('pen_type_group');
        document.getElementById('panel_pen').classList.add('active');
        const dropdown=group.parentElement,trigger=dropdown.querySelector('.tool-dropdown-trigger');
        dropdown.dispatchEvent(new MouseEvent('mouseenter'));
        check(getComputedStyle(group).display==='flex'&&trigger.getAttribute('aria-expanded')==='true','Hover did not open pen menu');
        group.querySelector('[data-val="charcoal"]').click();
        check(trigger.textContent.includes('목탄')&&!dropdown.classList.contains('open'),'Selection label or dismissal failed');
        for(const kind of NaturalPens.kinds){
            document.getElementById('set_pen_'+kind+'_weight').value=13;
            document.getElementById('set_pen_'+kind+'_opacity').value=42;
            document.getElementById('set_pen_'+kind+'_color').style.backgroundColor='#224466';
        }
        NaturalPens.readSettings();
        const settings=collectSettings();
        for(const kind of NaturalPens.kinds){
            check(settings['set_pen_'+kind+'_opacity']==='42','Density not saved');
            check(near(new fabric.Color(NaturalPens.defaults[kind].color).getAlpha(),Math.min(1,42/NaturalPens.densityBase[kind])),'Density not applied');
        }
        document.getElementById('pen_arrow').checked=true;
        try {
            for(const kind of ['ballpoint','highlighter','pencil','brush','charcoal']){
                activeTool='pen';const input=document.getElementById('pen_type');input.value=kind;input.dispatchEvent(new Event('change'));
                const brush=canvas.freeDrawingBrush;
                for(let repeat=0;repeat<2;repeat++){
                    activeTool='pen';canvas.isDrawingMode=true;
                    brush.onMouseDown({x:90,y:100},{e:{isPrimary:true}});
                    brush.onMouseMove({x:200,y:150},{e:{isPrimary:true}});
                    brush.onMouseMove({x:300,y:110},{e:{isPrimary:true}});
                    brush.onMouseUp({e:{isPrimary:true}});
                    const obj=canvas.getObjects().at(-1);
                    check(obj.penArrow,'Arrow missing on '+kind);
                    check(NaturalPens.arrowData(obj).endsWith('Z'),'Arrow geometry missing');
                    const restored=await new Promise(r=>fabric.util.enlivenObjects([obj.toObject()],items=>r(items[0])));
                    check(restored.penArrow&&restored.toDataURL()===obj.toDataURL(),'Arrow lost on restore');
                    const grain=NaturalPens.headTexture(obj,NaturalPens.arrowData(obj),obj.naturalPen,obj.naturalDensity,obj.penArrowType==='open');
                    check(obj.toSVG().includes(grain?grain.d:NaturalPens.arrowData(obj)),'Arrow missing in SVG');
                }
                const straight=new fabric.Path('M 100 250 L 320 300',{stroke:penCurrentColor,strokeWidth:13,naturalPen:NaturalPens.kinds.includes(kind)?kind:undefined});
                const center=straight.getCenterPoint();applyPenArrow(straight);
                check(straight.penArrow&&near(straight.getCenterPoint().x,center.x),'Straight arrow moved');
            }
        } finally {document.getElementById('pen_arrow').checked=false;}
        const plain=new fabric.Path('M 0 0 L 100 0');applyPenArrow(plain);check(!plain.penArrow,'Unchecked option ignored');
    });
    await test('pen arrows use curve tangents and settings; texture density has headroom', async () => {
        const curve=new fabric.Path('M 0 0 C 20 0 100 40 100 100 L 100.001 100',{strokeWidth:5,stroke:'black'});
        const frame=NaturalPens.arrowFrame(curve);
        check(near(frame.angle,Math.PI/2),'Tiny final segment corrupted tangent');
        check(near(frame.end.x,100)&&near(frame.end.y,100),'Arrow is not centered at endpoint');
        for(const type of ['triangle','stealth','open']) {
            document.getElementById('set_arrow_type').value=type;
            document.getElementById('pen_arrow').checked=true;applyPenArrow(curve);
            check(curve.penArrowType===type,'Arrow setting ignored');
            const d=NaturalPens.arrowData(curve);
            check(type==='open'?!d.endsWith('Z'):d.endsWith('Z'),'Wrong head geometry');
        }
        document.getElementById('set_arrow_type').value='triangle';document.getElementById('pen_arrow').checked=false;
        for(const [kind,base] of [['pencil',50],['charcoal',70]]){
            const pts=[{x:0,y:0},{x:200,y:0}];
            const legacy=NaturalPens.geometry(pts,kind,12,false);
            const baseline=NaturalPens.geometry(pts,kind,12,false,{x:0,y:0},base);
            const dense=NaturalPens.geometry(pts,kind,12,false,{x:0,y:0},100);
            check(legacy===baseline,'Baseline appearance changed');
            check(dense.length>baseline.length*1.3,'No density headroom');
        }
    });
    await test('floating toolbar reserves a separate canvas viewport even during scrolling', async () => {
        const toolbar=document.getElementById('sub_toolbar');
        toolbar.style.display='block';toolbar.style.top='65px';document.getElementById('panel_pen').classList.add('active');
        updateWorkspaceInset();
        check(workspace.getBoundingClientRect().top>=toolbar.getBoundingClientRect().bottom+10,'Toolbar overlaps workspace');
        workspace.dispatchEvent(new WheelEvent('wheel',{deltaY:200,clientX:400,clientY:400,cancelable:true}));
        check(workspace.getBoundingClientRect().top>=toolbar.getBoundingClientRect().bottom+10,'Scrolling removed clearance');
        toolbar.style.display='none';updateWorkspaceInset();
        check(near(workspace.getBoundingClientRect().top,60),'Viewport did not expand after closing: '+workspace.getBoundingClientRect().top);
    });
    await test('all five shape pens preserve fills, geometry, JSON and linked arrow style', async () => {
        const signatures=[];
        for(const kind of ShapePens.kinds){
            const objects=[new fabric.Rect({left:30,top:40,width:100,height:70}),new fabric.Ellipse({left:160,top:40,rx:50,ry:35}),
                new fabric.Polygon([{x:0,y:35},{x:50,y:0},{x:100,y:35},{x:50,y:70}],{left:290,top:40})];
            for(const obj of objects){
                obj.set({stroke:'#334455',strokeWidth:8,fill:'#ffddaa'});
                ShapePens.apply(obj,kind,kind==='highlighter'?30:100);canvas.add(obj);canvas.renderAll();
                const first=obj.toDataURL();
                const restored=await new Promise(r=>fabric.util.enlivenObjects([obj.toObject()],items=>r(items[0])));
                check(restored.shapePen===kind&&restored.toDataURL()===first,'Shape texture did not restore: '+kind);
                check(obj.fill==='#ffddaa'&&obj.stroke==='#334455','Renderer modified stored color');
                check(obj.toSVG().includes('<'),'SVG export failed');
                if(obj.type==='rect')signatures.push(first);
            }
            let arrow=line(true,'curve');ShapePens.apply(arrow,kind,75);
            recalculateAndRedrawLine(arrow,false);arrow=canvas.getActiveObject();
            check(arrow.shapePen===kind&&arrow.getObjects().every(o=>o.shapePen===kind),'Line rebuild lost pen style');
        }
        check(new Set(signatures).size===5,'Shape pens are not visually distinct');
        activeTool='shape';document.getElementById('shape_pen_type').value='charcoal';
        const created=new fabric.Rect({width:50,height:50,stroke:'black',strokeWidth:5,isTemp:true});canvas.add(created);
        check(created.shapePen==='charcoal','Drawing did not adopt chosen pen');
        activeTool=null;canvas.setActiveObject(created);
        document.getElementById('shape_pen_type').value='brush';document.getElementById('shape_pen_type').dispatchEvent(new Event('change'));
        check(created.shapePen==='brush','Selected shape pen did not change');
        document.getElementById('shape_pen_type').value='ballpoint';
    });
    await test('Gaussian mosaic smooths edges without transparent borders', async () => {
        canvas.clear();canvas.backgroundColor='white';
        canvas.add(new fabric.Rect({left:150,top:100,width:100,height:100,fill:'black',strokeWidth:0}));
        window.sysMosaicPx=8;
        applyMosaicToCanvas(100,110,100,60,'rect');
        await until(()=>canvas.getObjects().some(o=>o.isMosaic));
        const image=canvas.getObjects().find(o=>o.isMosaic);
        const c=document.createElement('canvas');c.width=100;c.height=60;
        const ctx=c.getContext('2d');ctx.drawImage(image.getElement(),0,0);
        const pixels=ctx.getImageData(0,30,100,1).data;
        const shades=new Set();
        for(let x=30;x<70;x++)shades.add(pixels[x*4]);
        check(shades.size>15,'Blur must have a smooth gradient, not pixel blocks');
        check(pixels[3]===255&&pixels[99*4+3]===255,'Blur introduced transparent edges');
        window.sysMosaicPx=3;
    });
    await test('pencil and charcoal arrowheads have cached grain in canvas and SVG', async () => {
        for(const kind of ['pencil','charcoal'])for(const type of ['triangle','stealth','open']){
            const pen=new fabric.Path('M 10 10 L 100 40',{stroke:'#333',strokeWidth:8,fill:null,naturalPen:kind,naturalDensity:100,penArrow:true,penArrowType:type});
            StrokeEffects.apply(pen,true);canvas.add(pen);canvas.renderAll();
            check(pen._headTexture?.d&&pen.toSVG().includes(pen._headTexture.d),'Wavy pen arrow lost its texture');
            const obj=line(true);obj.arrowType=type;
            const rebuilt=createLineShapeFromPoints(obj,obj.__capcraftPoints);
            ShapePens.apply(rebuilt,kind,100);canvas.add(rebuilt);canvas.renderAll();
            const heads=rebuilt.getObjects().filter(o=>o.isArrowHead);
            check(heads.length>0,'Missing arrowhead');
            for(const head of heads){
                check(head._headTexture?.d.includes('a'),'Head has no grain');
                const cached=head._headTexture;
                check(head.toSVG().includes(cached.d),'Head grain missing in SVG');
                canvas.renderAll();check(head._headTexture===cached,'Head texture regenerated without changes');
            }
        }
    });
    await test('charcoal filled heads retain shaft grain size and density', () => {
        const width=22;
        const head=createArrowHead(160,100,0,'triangle','m','#333',width);
        ShapePens.apply(head,'charcoal',70);
        canvas.add(head);canvas.renderAll();
        check(head.strokeWidth===0&&head.arrowStrokeWidth===width,'Head changed outline or lost shaft width');
        const grain=head._headTexture;
        check(JSON.parse(grain.key)[3]===width,'Head grain used one-pixel fallback');
        check(head.toObject().arrowStrokeWidth===width,'Saved head lost texture width');
        const c=document.createElement('canvas');c.width=200;c.height=160;
        const ctx=c.getContext('2d');ctx.translate(100,80);ctx.fill(grain.path);
        const a=ctx.getImageData(72,70,16,20).data;
        let opacity=0;for(let i=3;i<a.length;i+=4)opacity+=a[i]/255;
        check(opacity/(a.length/4)>.4,'Filled charcoal head remains too faint');
    });
    await test('mosaic rectangle and ellipse show temporary guides throughout dragging', async () => {
        const getPointer=canvas.getPointer;
        let point={x:180,y:180};
        canvas.getPointer=()=>point;
        try{
            for(const type of ['rect','ellipse']){
                document.querySelector('#mosaic_type_group [data-val="'+type+'"]').click();
                point={x:180,y:180};
                canvas.fire('mouse:down',{e:{button:0,clientX:180,clientY:180}});
                const guide=currentShape;
                check(guide&&canvas.getObjects().includes(guide),'Guide never added to canvas');
                for(const next of [{x:90,y:100},{x:300,y:270}]){
                    point=next;canvas.fire('mouse:move',{e:{clientX:next.x,clientY:next.y}});canvas.renderAll();
                    check(guide.width>0&&guide.height>0,'Guide has no area');
                    const left=type==='rect'?guide.left:guide.left-guide.rx;
                    check(near(left,Math.min(180,next.x)),'Guide drifts when crossing starting point');
                    check(guide.visible&&guide.stroke&&guide.fill,'Guide is invisible');
                }
                const before=canvas.getObjects().filter(o=>o.isMosaic).length;
                canvas.fire('mouse:up',{e:{button:0}});
                await until(()=>canvas.getObjects().filter(o=>o.isMosaic).length===before+1);
                check(!canvas.getObjects().includes(guide),'Guide left behind after applying mosaic');
            }
        }finally{canvas.getPointer=getPointer;}
    });
    await test('mosaic subtype activates tool and respects pin after insertion', async () => {
        const button=document.getElementById('btn_tool_mosaic'),pin=button.querySelector('.pin-icon');
        const wasPinned=pin.classList.contains('active');
        try {
            for(const pinned of [false,true])for(const type of ['rect','ellipse','freehand']){
                activeTool=null;button.classList.remove('active');pin.classList.toggle('active',pinned);
                document.querySelector('#mosaic_type_group [data-val="'+type+'"]').click();
                check(activeTool==='mosaic'&&button.classList.contains('active'),'Subtype did not activate mosaic');
                check(canvas.isDrawingMode===(type==='freehand'),'Wrong drawing mode');
                const before=canvas.getObjects().filter(o=>o.isMosaic).length;
                const mask=type==='freehand'?new fabric.Path('M 30 30 L 80 80',{stroke:'black',strokeWidth:20}):null;
                if(mask)canvas.add(mask);
                applyMosaicToCanvas(20,20,80,80,type,mask);
                await until(()=>canvas.getObjects().filter(o=>o.isMosaic).length===before+1);
                check((activeTool==='mosaic')===pinned,'Pin not respected after insertion');
                check(button.classList.contains('active')===pinned,'Toolbar active state wrong');
                if(pinned&&type==='freehand')check(canvas.isDrawingMode,'Pinned freehand did not resume');
            }
        } finally {pin.classList.toggle('active',wasPinned);activeTool=null;canvas.isDrawingMode=false;}
    });
    await test('shape pen selection loads each settings preset without double alpha', async () => {
        const saved=collectSettings();
        try {
            for(const [i,kind] of ShapePens.kinds.entries()){
                const width=7+i*3;
                document.getElementById('set_pen_'+kind+'_weight').value=width;
                document.getElementById('set_pen_'+kind+'_color').style.backgroundColor='rgba(20,80,140,0.3)';
                if(kind!=='ballpoint')document.getElementById('set_pen_'+kind+'_opacity').value=35;
                canvas.discardActiveObject();
                document.querySelector('#shape_pen_type_group [data-val="'+kind+'"]').click();
                check(Number(document.getElementById('shape_weight').value)===width,'Toolbar width not loaded');
                check(new fabric.Color(strokeColor).toRgb()==='rgb(20,80,140)','Toolbar color not loaded');
                const obj=new fabric.Rect({left:120,top:140,width:100,height:60,fill:'yellow',stroke:'red',strokeWidth:1});
                canvas.add(obj);canvas.setActiveObject(obj);
                document.querySelector('#shape_pen_type_group [data-val="'+kind+'"]').click();
                check(obj.shapePen===kind&&obj.strokeWidth===width,'Selected shape did not get preset');
                check(new fabric.Color(obj.stroke).getAlpha()===1,'Density applied twice');
                check(kind==='ballpoint'||obj.shapeDensity===35,'Density not loaded');
                check(obj.fill==='yellow'&&near(obj.left,120)&&near(obj.top,140),'Fill or position changed');
                const arrow=line(true,'polyline'),points=JSON.stringify(arrow.__capcraftPoints);
                document.querySelector('#shape_pen_type_group [data-val="'+kind+'"]').click();
                const updated=canvas.getActiveObject();
                check(updated.shapePen===kind&&updated.getObjects().find(o=>o.isArrowBody).strokeWidth===width,'Arrow preset lost');
                check(JSON.stringify(updated.__capcraftPoints)===points,'Preset moved arrow endpoints');
            }
        }finally{restoreSettings(JSON.stringify(saved));}
    });
    await test('clear all recent captures requires confirmation and clears canvas/history', async () => {
        canvas.add(new fabric.Rect({left:20,top:20,width:30,height:30,fill:'red'}));
        saveHistory();pushCurrentToRecent();renderRecentList();
        const count=recentList.length, objects=canvas.getObjects().length;
        document.getElementById('btn_recent_clear').click();
        check(document.getElementById('dialog_msg').innerText==='모두 삭제하시겠습니까?', 'Wrong confirmation message');
        check(document.getElementById('dialog_btn_ok').innerText==='확인' && document.getElementById('dialog_btn_cancel').innerText==='취소','Wrong confirmation labels');
        document.getElementById('dialog_btn_cancel').click();await wait(0);
        check(recentList.length===count && canvas.getObjects().length===objects,'Cancel deleted content');
        scheduleCurrentThumbnail(getCanvasJSON());
        document.getElementById('btn_recent_clear').click();document.getElementById('dialog_btn_ok').click();
        await wait(350);
        check(recentList.length===0 && activeRecentIdx===-1 && !hasActiveCanvas,'Recent records remain');
        check(canvas.getObjects().length===0 && !canvas.backgroundImage && stateHistory.length===0 && historyIndex===-1,'Canvas or undo retained deleted captures');
        check(document.getElementById('recent_list_container').children.length===0 && document.getElementById('btn_recent_clear').disabled,'Empty sidebar not updated');
    });
    await test('offscreen thumbnail preserves pending visible selection and color paint', async () => {
        const obj=new fabric.Rect({left:100,top:100,width:120,height:80,fill:'#ff0000',strokeWidth:0});
        canvas.add(obj);canvas.renderAll();
        let visiblePaints=0;
        const onRender=e=>{if(e.ctx===canvas.contextContainer) visiblePaints++;};
        canvas.on('after:render',onRender);
        try {
            canvas.setActiveObject(obj);
            obj.set('fill','#00ff00');
            canvas.requestRenderAll();
            pushCurrentToRecent();
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            check(visiblePaints>0,'Thumbnail cancelled visible selection/color repaint');
            const p=fabric.util.transformPoint(obj.getCenterPoint(),canvas.viewportTransform);
            const ratio=canvas.getRetinaScaling();
            const color=canvas.contextContainer.getImageData(p.x*ratio,p.y*ratio,1,1).data;
            check(color[1]>240 && color[0]<10,'Color not painted until another interaction');
            visiblePaints=0;
            obj.controls.flipX.mouseDownHandler({}, {target:obj});
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            check(obj.flipX && visiblePaints>0,'Flip control did not paint without another click');
        } finally {canvas.off('after:render',onRender);}
    });
    await test('five-object clicks select and paint the current target without snapshot work', async () => {
        isHistoryAction = true;
        const objects = Array.from({ length: 5 }, (_, i) => new fabric.Rect({
            id: `click-target-${i + 1}`, left: 40 + i * 140, top: 160,
            width: 90, height: 90, fill: `hsl(${i * 65} 80% 55%)`
        }));
        canvas.add(...objects);
        isHistoryAction = false;
        initHistory();
        cancelPendingThumbnail();

        let exports = 0;
        const originalExport = canvas.toCanvasElement;
        canvas.toCanvasElement = function (...args) {
            exports++;
            return originalExport.apply(this, args);
        };
        try {
            const painted = [];
            const onRender = () => painted.push(canvas.getActiveObject()?.id || null);
            canvas.on('after:render', onRender);
            try {
                for (const obj of objects) {
                    canvas.setActiveObject(obj);
                    const center = obj.getCenterPoint();
                    canvas.fire('mouse:down', {
                        target: obj,
                        e: { clientX: center.x, clientY: center.y, button: 0,
                            ctrlKey: false, shiftKey: false, metaKey: false }
                    });
                    check(canvas.getActiveObject() === obj, `Click selected stale object instead of ${obj.id}`);
                    check(painted[painted.length - 1] === obj.id, `Visible frame lagged behind ${obj.id}`);
                }
                await wait(300);
                check(exports === 0, 'Plain selection generated a thumbnail/export');
            } finally { canvas.off('after:render', onRender); }
        } finally { canvas.toCanvasElement = originalExport; }
    });
    await test('property edit paints before deferred thumbnail export', async () => {
        const obj = new fabric.Rect({ id: 'edited-object', left: 120, top: 120, width: 120, height: 90, fill: '#ff0000' });
        canvas.add(obj); canvas.setActiveObject(obj); canvas.renderAll();
        cancelPendingThumbnail();
        let exports = 0;
        const originalExport = canvas.toCanvasElement;
        canvas.toCanvasElement = function (...args) { exports++; return originalExport.apply(this, args); };
        try {
            obj.set('fill', '#00ff00'); obj.set('dirty', true);
            canvas.requestRenderAll(); saveHistory();
            check(exports === 0, 'Property edit exported before the visible frame');
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const p = fabric.util.transformPoint(obj.getCenterPoint(), canvas.viewportTransform);
            const ratio = canvas.getRetinaScaling();
            const color = canvas.contextContainer.getImageData(p.x * ratio, p.y * ratio, 1, 1).data;
            check(color[1] > 240 && color[0] < 10, 'Property edit was not visible immediately');
            await wait(300);
            check(exports === 1, `Expected one deferred thumbnail, got ${exports}`);
        } finally { canvas.toCanvasElement = originalExport; }
    });
    await test('offline emoji data and icons', async () => {
        const picker = document.getElementById('ep_main');
        await customElements.whenDefined('emoji-picker');
        const emoji = await picker.database.getEmojiByUnicodeOrName('😀');
        check(emoji?.unicode === '😀', 'Offline emoji database unavailable');
        check(document.querySelectorAll('svg.lucide').length > 20, 'Toolbar icons missing');
    });
    for (const arrow of [false, true]) for (const type of ['polyline', 'curve']) {
        await test(`${arrow ? 'arrow' : 'line'} ${type}: anchor hover and drag`, () => {
            const obj = line(arrow, type), h = obj.__capcraftHandles[1];
            const x = h.left, y = h.top;
            canvas.fire('mouse:over', { target: h });
            check(h.radius === 12 && h.shadow && h.hoverCursor === 'default', 'Hover style missing');
            check(h.left === x && h.top === y, 'Hover moved anchor');
            canvas.fire('mouse:out', { target: h });
            check(h.radius === 8 && !h.shadow, 'Hover style not restored');
            h.set({ left: x + 30, top: y + 25 });
            canvas.fire('object:moving', { target: h });
            check(near(obj.__capcraftPoints[1].x, x + 30), 'Anchor did not update geometry');
            check(!JSON.parse(getCanvasJSON()).objects.some(o => o.isTemp), 'Temporary anchors serialized');
        });
    }
    await test('wavy arrows keep endpoints stable during repeated handle drags', () => {
        for(const type of ['normal','polyline','curve']) {
            const obj=line(true,type);StrokeEffects.apply(obj,true);
            if(type==='normal'){delete obj.arrowType;delete obj.arrowSize;obj.getObjects()[0].arrowType='triangle';obj.getObjects()[0].arrowSize='m';}
            canvas.renderAll();
            for(const index of [0,obj.__capcraftPoints.length-1])for(let n=0;n<5;n++){
                const handle=obj.__capcraftHandles[index],x=handle.left+7,y=handle.top-9;
                handle.set({left:x,top:y});
                try{canvas.fire('object:moving',{target:handle});canvas.renderAll();}
                catch(e){throw new Error(e.stack);}
                const body=obj.getObjects().find(o=>o.isArrowBody);
                const first=body.path[0],point=fabric.util.transformPoint(new fabric.Point(first[1]-body.pathOffset.x,first[2]-body.pathOffset.y),body.calcTransformMatrix());
                check(near(point.x,obj.__capcraftPoints[0].x)&&near(point.y,obj.__capcraftPoints[0].y),'Rendered start jumped: '+JSON.stringify(point));
            }
            canvas.remove(obj);removeLineHandles(obj);
        }
    });
    await test('line label growth, body movement and flip', async () => {
        let obj = line();
        document.getElementById('btn_add_text_to_shape').click();
        const text = obj.linkedText;
        text.set('text', '한글 ABC 넓은 글자 WWWWWWWWWWW'); text.fire('changed');
        check(text.width > 200, 'Line label did not expand');
        text.exitEditing(); canvas.setActiveObject(obj);
        const originalX = obj.__capcraftPoints[0].x;
        canvas.fire('before:transform', { transform: { target: obj, original: { left: obj.left, top: obj.top } } });
        obj.set({ left: obj.left + 30, top: obj.top + 20 });
        canvas.fire('object:moving', { target: obj });
        check(near(obj.__capcraftPoints[0].x, originalX + 30), 'First body drag lost its delta');
        check(near(obj.__capcraftHandles[0].left, originalX + 30), 'Anchor did not follow body');
        const mid = getLineMidpoint(obj);
        check(near(text.left, mid.x) && near(text.top, mid.y), 'Label did not follow body');
        canvas.fire('object:modified', { target: obj });
        const id = obj.id;
        flipLineOrArrow(obj, 'x'); await wait(50);
        obj = canvas.getActiveObject();
        check(obj.id === id, 'Flip lost persistent ID');
        check(obj.linkedText === text && text.linkedShape === obj, 'Flip detached label');
        const json = getCanvasJSON();
        await new Promise(r => canvas.loadFromJSON(json, r, window.popoutReviver));
        restoreLinkedTexts();
        const restored = canvas.getObjects().find(o => o.id === id);
        check(restored?.linkedText?.linkedShape === restored, 'JSON round trip detached flipped label');
    });
    await test('pen pin survives freehand and curve correction', () => {
        document.querySelector('#btn_tool_pen .pin-icon').classList.add('active');
        document.getElementById('btn_tool_pen').click();
        for (const corrected of [false, true]) {
            _isAutoShapeTriggered = corrected;
            const path = new fabric.Path('M 100 100 Q 130 170 180 140 Q 240 90 300 180', { stroke: '#ff0000', strokeWidth: 3 });
            canvas.add(path); canvas.fire('path:created', { path });
            check(activeTool === 'pen' && canvas.isDrawingMode, 'Pinned pen deactivated');
            check(document.getElementById('btn_tool_pen').classList.contains('active'), 'Pen button inactive');
        }
    });
    await test('shape opacity and color preserve cached geometry and visible pixels', () => {
        const obj = new fabric.Rect({left:200,top:180,width:240,height:160,
            fill:'rgba(0,140,180,0.29)',stroke:'red',strokeWidth:3});
        canvas.add(obj); canvas.setActiveObject(obj); canvas.renderAll();
        const geometry = JSON.stringify([obj.left,obj.top,obj.width,obj.height,obj.scaleX,obj.scaleY]);
        const cache = obj._cacheCanvas;
        const assertPaint = () => {
            check(JSON.stringify([obj.left,obj.top,obj.width,obj.height,obj.scaleX,obj.scaleY]) === geometry,
                'Property edit changed geometry');
            check(obj._cacheCanvas === cache, 'Property edit replaced initialized cache');
            const t = obj._cacheContext.getTransform();
            check(near(t.e,obj.cacheTranslationX) && near(t.f,obj.cacheTranslationY),
                'Cache lost its origin transform');
            const pixel = obj._cacheContext.getImageData(obj.cacheTranslationX,obj.cacheTranslationY,1,1).data;
            check(pixel[3] > 0, 'Shape center missing from cache');
        };
        for (const value of [72,71,50,0,85]) {
            handleShapeBgOpacityChange(value); canvas.renderAll(); assertPaint();
        }
        updateActiveShapeProperties({fill:'#00aaee'}); canvas.renderAll(); assertPaint();
    });
    await test('shape, pen and text transparency settings sync', () => {
        const pairs = [['shape_bg_opacity_input', 'set_shape_opacity_val'], ['pen_bg_opacity_input', 'set_pen_bg_opacity'], ['text_bg_opacity_input', 'set_txt_bg_opacity']];
        for (const [toolbar, setting] of pairs) {
            const el = document.getElementById(toolbar); el.value = '35'; el.dispatchEvent(new Event('input'));
            check(document.getElementById(setting).value === '35', toolbar + ' did not sync to settings');
            document.getElementById(setting).value = '70'; applySettings();
            check(el.value === '70', setting + ' did not sync to toolbar');
        }
    });
    await test('pen fill can return from fully transparent', () => {
        const path = new fabric.Path('M 100 100 L 200 200 L 300 100 z', { fill: '#ff0000', stroke: '#ff0000' });
        canvas.add(path); canvas.setActiveObject(path);
        handlePenBgOpacityChange(100); check(path.fill === 'transparent', '100% must be transparent');
        handlePenBgOpacityChange(35);
        check(near(new fabric.Color(path.fill).getAlpha(), 0.65), 'Pen stayed invisible after reducing transparency');
    });
    await test('JSON export includes background and dimensions', async () => {
        const source = document.createElement('canvas'); source.width = 420; source.height = 260;
        source.getContext('2d').fillRect(0, 0, 420, 260);
        const img = await new Promise(r => fabric.Image.fromURL(source.toDataURL(), r));
        canvas.setWidth(420); canvas.setHeight(260); canvas.backgroundImage = img;
        const saved = JSON.parse(await getSaveBlobAndName('json').blob.text());
        check(saved.width === 420 && saved.height === 260, 'Export lost canvas dimensions');
        check(!!saved.backgroundImage?.src, 'Export lost capture image');
        check(saved.background === '#f0e0d0' || saved.backgroundColor === '#f0e0d0', 'Export lost background color');
    });
    await test('SVG export excludes executable markup', async () => {
        const obj = new fabric.Rect({ left: 20, top: 20, width: 50, height: 40, fill: '#ff0000' });
        obj.id = 'unsafe" onload="alert(1)'; canvas.add(obj);
        const svg = await getSaveBlobAndName('svg').blob.text();
        check(!/onload\s*=|<script|<foreignObject/i.test(svg), 'Unsafe SVG attribute survived');
        check(svg.includes('<rect'), 'SVG shape was lost');
    });
    await test('Undo/Redo keeps background color and linked text', async () => {
        const obj = new fabric.Rect({ left: 200, top: 200, width: 180, height: 140, fill: '#00aaff' });
        canvas.add(obj); canvas.setActiveObject(obj); document.getElementById('btn_add_text_to_shape').click();
        obj.linkedText.set('text', '연결 테스트'); obj.linkedText.exitEditing(); saveHistory();
        const savedIdx = historyIndex;
        canvas.add(new fabric.Rect({ width: 20, height: 20 }));
        saveHistory(); const redoIdx = historyIndex;
        loadHistoryState(savedIdx); await until(() => !isHistoryAction);
        check(canvas.backgroundColor === '#f0e0d0', 'Undo lost background color');
        const restored = canvas.getObjects().find(o => o.id === obj.id);
        check(restored?.linkedText?.text === '연결 테스트', 'Undo lost text link');
        const count = canvas.getObjects().length;
        loadHistoryState(redoIdx); await until(() => !isHistoryAction);
        check(canvas.getObjects().length === count + 1, 'Redo did not restore added object');
    });
    await test('popout defaults, JSON links and undo', async () => {
        const obj = new fabric.Rect({ left: 200, top: 200, width: 120, height: 90, fill: 'transparent', stroke: '#ff0000' });
        canvas.add(obj); createPopoutFromObject(obj);
        await until(() => canvas.getObjects().some(o => o.isPopout));
        let pop = canvas.getObjects().find(o => o.isPopout);
        check(pop.angle === Number(document.getElementById('set_popout_angle').value), 'Popout angle default ignored');
        check(pop.linkedLine && pop.linkedOriginal === obj, 'Popout links missing');
        check(pop._croppedBg.width >= pop._popoutSourceWidth*3.9, 'Source snapshot was screen-resolution');
        check(pop._element.width >= pop.width*1.9, 'Final raster was not supersampled');
        pop.popoutSharpness = 62; regeneratePopoutBase(pop); saveHistory();
        const savedIdx = historyIndex, sourceWidth = pop._popoutSourceWidth;
        const json = getCanvasJSON();
        isHistoryAction=true;
        await new Promise(r => canvas.loadFromJSON(json, r, window.popoutReviver)); restorePopoutLinks();
        isHistoryAction=false;
        await until(() => canvas.getObjects().find(o => o.isPopout)?._croppedBg);
        pop = canvas.getObjects().find(o => o.isPopout);
        check(pop.linkedOriginal?.id === obj.id && pop.linkedLine, 'Popout round trip lost links');
        check(pop.linkedLine.startLinkedObj===pop.linkedOriginal && pop.linkedLine.endLinkedObj===pop,
            'Restored segment endpoints lost object references');
        check(pop._popoutSourceWidth === sourceWidth && pop.popoutSharpness === 62, 'Quality settings lost in JSON');
        const w = pop.width; pop.set({scaleX:3,scaleY:3});
        canvas.fire('object:modified', { target: pop });
        check(near(pop.width,w) && pop._element.width >= pop.width*2.9, 'Resize did not retain logical size / raise raster resolution');
        loadHistoryState(savedIdx); await until(() => !isHistoryAction);
        await until(() => canvas.getObjects().find(o => o.isPopout)?._croppedBg);
        pop = canvas.getObjects().find(o => o.isPopout);
        check(pop.popoutSharpness === 62 && pop.linkedOriginal && pop.scaleX === 1, 'Popout undo lost settings or links');
        const markup = pop._toSVG().join('');
        check(markup.includes('width="'+pop.width+'"'), 'SVG used raster dimensions as logical dimensions');
    });
    await test('popout snapshot independent of viewport, no visible repaint', () => {
        const mark = new fabric.Rect({left:210,top:210,width:30,height:30,fill:'#ff0000',strokeWidth:0});
        const mask = new fabric.Rect({left:200,top:200,width:100,height:80,fill:'transparent',strokeWidth:0});
        canvas.add(mark,mask); canvas.setViewportTransform([2,0,0,2,-90,-70]);
        const before = canvas.viewportTransform.slice(), objects = canvas._objects;
        let renders=0; const render=canvas.renderAll;
        canvas.renderAll = function() { renders++; return render.apply(this,arguments); };
        let shot;
        try { shot=CapcraftPopout.snapshot(canvas,mask); } finally { canvas.renderAll=render; }
        const pixel=shot.image.getContext('2d').getImageData(80,80,1,1).data;
        check(pixel[0]===255 && pixel[1]===0, 'Snapshot crop was distorted by zoom/pan');
        check(JSON.stringify(canvas.viewportTransform)===JSON.stringify(before) && canvas._objects===objects, 'Snapshot changed canvas state');
        check(renders===0, 'Snapshot repainted the visible canvas');
        canvas.setViewportTransform([1,0,0,1,0,0]);
    });
    await test('popout connector is an editable linked normal segment', async () => {
        const mask=new fabric.Rect({left:100,top:100,width:100,height:80,fill:'transparent'});
        canvas.add(mask);createPopoutFromObject(mask);
        await until(()=>canvas.getObjects().some(o=>o.isPopout));
        const pop=canvas.getObjects().find(o=>o.isPopout);
        pop.showConnectionLine=true;updatePopoutLine(pop);
        let line=pop.linkedLine;
        check(line.type==='path' && line.__capcraftLineType==='normal' && line.selectable && line.evented,'Not a regular selectable segment');
        check(line.startLinkedObj===mask && line.endLinkedObj===pop,'Both ends must be linked');
        const before=JSON.stringify(line.__capcraftPoints);
        pop.left+=150;canvas.fire('object:moving',{target:pop});
        check(JSON.stringify(line.__capcraftPoints)!==before,'Endpoint failed to follow popout');
        canvas.setActiveObject(line);line.left+=30;canvas.fire('object:moving',{target:line});
        check(!line.startLinkedObj && !line.endLinkedObj,'Segment movement should detach like a regular segment');
        canvas.fire('object:modified',{target:line});
        line=pop.linkedLine;
        check(canvas.getObjects().includes(line),'Moving segment lost its owner reference');
        canvas.remove(line);
        check(!pop.linkedLine && !pop.showConnectionLine && canvas.getObjects().includes(pop),'Independent deletion failed');
        canvas.setActiveObject(pop);
        const toggle=document.getElementById('popout_line_toggle');
        toggle.checked=true;toggle.dispatchEvent(new Event('change'));
        check(pop.linkedLine?.startLinkedObj===mask && pop.linkedLine?.endLinkedObj===pop,'Checkbox did not recreate segment');
        toggle.checked=false;toggle.dispatchEvent(new Event('change'));
        check(!pop.linkedLine && !canvas.getObjects().some(o=>o.isPopoutLine),'Unchecked connector remains on canvas');
        const secondMask=new fabric.Rect({left:300,top:100,width:80,height:70,fill:'transparent'});
        canvas.add(secondMask);createPopoutFromObject(secondMask);
        await until(()=>canvas.getObjects().filter(o=>o.isPopout).length===2);
        const second=canvas.getObjects().find(o=>o.isPopout && o!==pop);
        check(!second.linkedLine && !second.showConnectionLine,'Creation ignored unchecked toolbar');
        canvas.setActiveObject(second);toggle.checked=true;toggle.dispatchEvent(new Event('change'));
        check(second.linkedLine?.endLinkedObj===second,'Initially unchecked popout cannot create a connector');
    });
    await test('popout movement reuses pixels and PNG; batched quality input invalidates cache', async () => {
        const mask=new fabric.Rect({left:100,top:100,width:160,height:100,fill:'transparent'});
        canvas.add(mask);createPopoutFromObject(mask);
        await until(()=>canvas.getObjects().some(o=>o.isPopout));
        const pop=canvas.getObjects().find(o=>o.isPopout), raster=pop._element;
        let encodes=0;
        const encode=raster.toDataURL.bind(raster);
        raster.toDataURL=(...args)=>{encodes++;return encode(...args);};
        pop._popoutEncodedElement=null;
        getCanvasJSON(); const firstEncodes=encodes;
        for(let i=0;i<5;i++) {
            pop.left+=2;pop._baseLeft+=2;
            canvas.fire('object:modified',{target:pop});
            check(pop._element===raster,'Movement recreated raster');
        }
        check(firstEncodes===1 && encodes===1,'History repeatedly encoded unchanged PNG');
        const input=document.getElementById('popout_sharpness');
        canvas.setActiveObject(pop);
        for(const value of [20,30,40,60]) {input.value=value;input.dispatchEvent(new Event('input'));}
        check(pop._element===raster,'Rapid input ran expensive processing synchronously');
        input.dispatchEvent(new Event('change'));
        check(pop._element!==raster && pop._sharpStrength===60,'Final input did not refresh pixels');
        const changedJSON=JSON.parse(getCanvasJSON()).objects.find(o=>o.isPopout);
        check(changedJSON.popoutSharpness===60 && changedJSON.src===pop.getSrc(),'History retained stale raster');
    });
    await test('popout tilt refreshes bounds to visible pixels', async () => {
        const mask=new fabric.Ellipse({left:100,top:100,rx:90,ry:55,fill:'transparent'});
        canvas.add(mask);createPopoutFromObject(mask);
        await until(()=>canvas.getObjects().some(o=>o.isPopout));
        const pop=canvas.getObjects().find(o=>o.isPopout);
        for(const [x,y] of [[20,-25],[0,0],[-35,40],[10,-10]]) {
            pop.tiltX=x;pop.tiltY=y;applyPopoutTilt(pop);
            const raster=pop._element, data=raster.getContext('2d').getImageData(0,0,raster.width,raster.height).data;
            let left=raster.width,top=raster.height,right=-1,bottom=-1;
            for(let py=0;py<raster.height;py++)for(let px=0;px<raster.width;px++)if(data[(py*raster.width+px)*4+3]) {
                left=Math.min(left,px);right=Math.max(right,px);top=Math.min(top,py);bottom=Math.max(bottom,py);
            }
            check(left<=1 && top<=1 && raster.width-1-right<=1 && raster.height-1-bottom<=1,'Selection includes stale transparent margins');
            check(near(pop.aCoords.tl.x,pop.calcACoords().tl.x),'Control coordinates stale');
        }
    });
    await test('popout resize preserves opposite anchor through raster regeneration', async () => {
        const mask=new fabric.Ellipse({left:100,top:100,rx:60,ry:40,fill:'transparent'});
        canvas.add(mask);createPopoutFromObject(mask);
        await until(()=>canvas.getObjects().some(o=>o.isPopout));
        const pop=canvas.getObjects().find(o=>o.isPopout);
        pop.tiltX=20;pop.tiltY=-25;pop.angle=4;applyPopoutTilt(pop);
        const point=(x,y)=>pop.getPointByOrigin(x,y);
        for (const [x,y,scale] of [['left','top',3],['right','bottom',1.2],
            ['left','bottom',2.7],['right','top',1],['center','center',2.4]]) {
            const anchor=point(x,y), raster=pop._element;
            pop.set({scaleX:scale,scaleY:scale});
            pop.setPositionByOrigin(anchor,x,y);pop.setCoords();
            canvas.fire('object:scaling',{target:pop});
            check(near(point(x,y).x,anchor.x)&&near(point(x,y).y,anchor.y),'Anchor moved during scaling');
            canvas.fire('object:modified',{target:pop});
            check(pop._element!==raster,'Test did not exercise resolution refresh');
            check(near(point(x,y).x,anchor.x)&&near(point(x,y).y,anchor.y),'Anchor jumped on mouse release: '+x+'/'+y);
            const position=[pop.left,pop.top];
            pop.popoutSharpness=pop.popoutSharpness===35?40:35;regeneratePopoutBase(pop);
            check(near(pop.left,position[0])&&near(pop.top,position[1]),'Quality change restored stale position');
        }
    });
    await test('conservative luminance sharpening, off switch and immutable source', () => {
        const source=document.createElement('canvas'); source.width=64; source.height=16;
        const ctx=source.getContext('2d');
        ctx.fillStyle='rgb(90,100,110)';ctx.fillRect(0,0,32,16);
        ctx.fillStyle='rgb(160,170,180)';ctx.fillRect(32,0,32,16);
        const before=source.toDataURL();
        check(CapcraftPopout.sharpen(source,0,64).toDataURL()===before, 'Off switch changed image');
        const out=CapcraftPopout.sharpen(source,35,64), pixels=out.getContext('2d').getImageData(0,0,64,16).data;
        check(out.toDataURL()!==before && source.toDataURL()===before, 'Sharpening ineffective or overwrote original: '+JSON.stringify({sameOutput:out.toDataURL()===before,sameSource:source.toDataURL()===before,edge:Array.from(pixels.slice((8*64+31)*4,(8*64+33)*4))}));
        for(let i=0;i<pixels.length;i+=4) check(pixels[i+1]-pixels[i]===10 && pixels[i+2]-pixels[i+1]===10 && pixels[i+3]===255, 'Sharpening changed chroma/alpha');
    });
    await test('multi-selection geometry', () => {
        const a = new fabric.Rect({ left: 100, top: 100, width: 50, height: 50 });
        const b = new fabric.Rect({ left: 200, top: 100, width: 50, height: 50 });
        canvas.add(a, b);
        const found = getObjectsInRect(canvas, { left: 90, top: 90, width: 180, height: 90 });
        check(found.includes(a) && found.includes(b), 'Region selection missed objects');
        const old = a.getCenterPoint().x;
        const selection = new fabric.ActiveSelection([a, b], { canvas }); canvas.setActiveObject(selection);
        selection.left += 30; canvas.fire('object:moving', { target: selection });
        canvas.discardActiveObject();
        check(near(a.getCenterPoint().x, old + 30), 'Selection movement incorrect');
    });
    await test('region-selected linked lines and arrows move once with their selection', () => {
        for(const arrow of [false,true]){
            const box=new fabric.Rect({left:80,top:80,width:60,height:60,fill:'blue',id:'multi-source'});
            canvas.add(box);
            const wire=line(arrow);removeLineHandles(wire);canvas.discardActiveObject();
            wire.startLinkedObj=box;wire.startAnchor=LineAnchors.capture(box,wire.__capcraftPoints[0]);
            const body=()=>wire.type==='group'?wire.getObjects().find(o=>o.isArrowBody):wire;
            const start=()=>{const b=body(),p=b.path[0];return fabric.util.transformPoint(new fabric.Point(p[1]-b.pathOffset.x,p[2]-b.pathOffset.y),b.calcTransformMatrix());};
            const original=start(),points=wire.__capcraftPoints.map(p=>({...p}));
            const selection=new fabric.ActiveSelection([box,wire],{canvas});canvas.setActiveObject(selection);
            canvas.fire('before:transform',{transform:{target:selection}});
            for(let i=1;i<=3;i++){
                selection.left+=15;selection.top+=10;
                canvas.fire('object:moving',{target:selection});canvas.renderAll();
                const p=start();
                check(near(p.x,original.x+15*i)&&near(p.y,original.y+10*i),'Selected line received selection translation twice');
                check(near(wire.__capcraftPoints[0].x,points[0].x+15*i),'Logical endpoints drifted');
            }
            canvas.fire('object:modified',{target:selection});
            canvas.discardActiveObject();
            check(near(start().x,original.x+45),'Deselect moved line');
            check(wire.startLinkedObj===box,'Multi-selection movement disconnected the selected target');
            const anchor=JSON.stringify(wire.startAnchor);
            box.left+=12;box.top+=8;
            updateLinkedLinesOnTransform(box);canvas.renderAll();
            check(near(wire.__capcraftPoints[0].x,points[0].x+57)&&near(wire.__capcraftPoints[0].y,points[0].y+38),'Retained connection did not follow subsequent target movement');
            check(JSON.stringify(wire.startAnchor)===anchor,'Fixed connection anchor changed');
            canvas.remove(wire,box);
        }
    });
    await test('different captures remain distinct in recent history', async () => {
        const sample = document.createElement('canvas'); sample.width = 80; sample.height = 60;
        for (const color of ['#ff0000', '#00ff00', '#0000ff']) {
            const ctx = sample.getContext('2d'); ctx.fillStyle = color; ctx.fillRect(0, 0, 80, 60);
            receiveCapturedImage(sample.toDataURL().split(',')[1]);
            await until(() => !isHistoryAction && canvas.width === 80);
        }
        check(new Set(recentList.filter(r => r.bgSrc).map(r => r.bgSrc)).size === 3, 'Distinct screenshots were deduplicated');
    });
    await test('rapid recent switching keeps records intact and commits only last request', async () => {
        const current=recentList[activeRecentIdx];
        const fixture=id=>({json:JSON.stringify({objects:[new fabric.Rect({id,left:100,top:100,width:70,height:50,fill:'red'}).toObject()]}),width:800,height:600,bgColor:'white'});
        recentList=[current,fixture('first'),fixture('last')];activeRecentIdx=0;renderRecentList();
        const original=recentList.map(x=>x.json);
        let saves=0;const save=triggerHistorySave;triggerHistorySave=()=>saves++;
        try {
            loadRecentItem(1);loadRecentItem(2);
            check(activeRecentIdx===0,'Active index changed before restore completed');
            document.getElementById('btn_tool_shape').click();
            document.querySelector('#shape_type_group button[data-val="ellipse"]').click();
            await until(()=>!_recentLoading);
            check(activeRecentIdx===2 && canvas.getObjects().some(o=>o.id==='last'),'Last request did not win');
            check(recentList.every((x,i)=>x.json===original[i]),'Switching overwrote a record without editing');
            check(saves===0,'Read-only switch scheduled disk persistence');
            check(activeTool==='shape' && document.getElementById('shape_type').value==='ellipse','Restore undid toolbar input');
            const after=recentList.map(x=>x.json);saves=0;
            loadRecentItem(1);await until(()=>!_recentLoading);
            check(saves===0 && recentList.every((x,i)=>x.json===after[i]),'First departure from restored item created a spurious edit');
        } finally {triggerHistorySave=save;}
    });
    await test('return to current recent item cancels pending restore', async () => {
        const current=recentList[activeRecentIdx];
        recentList=[current,{json:'{"objects":[]}',width:120,height:100,bgColor:'red'}];activeRecentIdx=0;
        loadRecentItem(1);loadRecentItem(0);
        await until(()=>!_recentLoading);
        check(activeRecentIdx===0 && canvas.width===800,'Pending restore overrode return to current item');
    });
    await test('new canvas supersedes pending recent restore', async () => {
        const current=recentList[activeRecentIdx];
        recentList=[current,{json:'{"objects":[]}',width:120,height:100,bgColor:'red'}];activeRecentIdx=0;
        loadRecentItem(1);commitLoadToCanvas(null,333,222,'#123456');
        await until(()=>!_recentLoading);
        check(canvas.width===333 && canvas.height===222,'Old request overwrote new capture');
        check(!isHistoryAction && canvas.upperCanvasEl.style.pointerEvents!=='none','Canvas input remained blocked');
    });
    await test('invalid recent record preserves displayed canvas and unlocks input', async () => {
        const current=recentList[activeRecentIdx];
        recentList=[current,{json:'invalid json',width:120,height:100}];activeRecentIdx=0;
        loadRecentItem(1);await until(()=>!_recentLoading);
        check(activeRecentIdx===0 && canvas.width===800,'Failed restore replaced current canvas');
        check(!isHistoryAction && canvas.upperCanvasEl.style.pointerEvents!=='none','Failed restore blocked input');
    });
    await test('70 successive capture loads and export formats', async () => {
        const sample = document.createElement('canvas'); sample.width = 80; sample.height = 60;
        const data = sample.toDataURL().split(',')[1];
        for (let i = 0; i < 70; i++) {
            receiveCapturedImage(data); await until(() => !isHistoryAction && canvas.width === 80);
        }
        check(recentList.length > 0 && hasActiveCanvas, 'Repeated capture load stalled');
        for (const format of ['png', 'jpg', 'svg', 'pdf', 'json']) {
            check(getSaveBlobAndName(format).blob.size > 20, format + ' export empty');
        }
    });
    return results;
};
