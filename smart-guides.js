/* Alignment overlay is not a Fabric object: it never enters exports or history. */
window.installSmartGuides = function(canvas) {
    const ns='http://www.w3.org/2000/svg', overlay=document.createElementNS(ns,'svg');
    overlay.id='smart_alignment_guides';overlay.setAttribute('aria-hidden','true');
    overlay.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:5;display:none';
    canvas.wrapperEl.appendChild(overlay);
    const lines=['x','y'].map(()=>{const line=document.createElementNS(ns,'line');line.setAttribute('stroke','#ec4899');overlay.appendChild(line);return line;});
    let session=null;
    const eligible=o=>o && o.visible!==false && o.selectable!==false && !o.isTemp && !o.__isLineHandle && !o.isBgImage && o!==canvas.backgroundImage;
    const bounds=o=>o.getBoundingRect(true,true);
    const values=(b,axis)=>axis==='x'?[b.left,b.left+b.width/2,b.left+b.width]:[b.top,b.top+b.height/2,b.top+b.height];
    function clear(){session=null;overlay.style.display='none';}
    function begin(target){
        clear();if(!eligible(target))return;
        const excluded=new Set([target]);
        if(target.type==='activeSelection')target.getObjects().forEach(o=>excluded.add(o));
        for(const o of [...excluded]){if(o.linkedText)excluded.add(o.linkedText);if(o.linkedShape)excluded.add(o.linkedShape);}
        const candidates={x:[0,canvas.width/2,canvas.width],y:[0,canvas.height/2,canvas.height]};
        canvas.getObjects().forEach(o=>{
            // Moving connectors and linked labels are not stationary references.
            if(!eligible(o)||excluded.has(o)||excluded.has(o.startLinkedObj)||excluded.has(o.endLinkedObj))return;
            const b=bounds(o);for(const axis of ['x','y'])candidates[axis].push(...values(b,axis));
        });
        for(const axis of ['x','y'])candidates[axis]=[...new Set(candidates[axis])].sort((a,b)=>a-b);
        session={target,candidates,held:{}};
    }
    function nearest(sorted,value){
        let lo=0,hi=sorted.length;
        while(lo<hi){const mid=(lo+hi)>>1;if(sorted[mid]<value)lo=mid+1;else hi=mid;}
        return [sorted[lo-1],sorted[lo]].filter(Number.isFinite);
    }
    function match(axis,points,tolerance){
        const held=session.held[axis];
        if(held && Math.abs(held.value-points[held.index])<=tolerance*1.6)return {...held,delta:held.value-points[held.index]};
        let best=null;
        points.forEach((p,index)=>nearest(session.candidates[axis],p).forEach(value=>{
            const delta=value-p;
            if(Math.abs(delta)<=tolerance&&(!best||Math.abs(delta)<Math.abs(best.delta)))best={value,index,delta};
        }));return best;
    }
    canvas.on('before:transform',e=>begin(e.transform.target));
    // Register before existing connection listeners so they use the snapped position.
    canvas.on('object:moving',e=>{
        const obj=e.target;
        if(!e.e||!eligible(obj)||(e.transform&&e.transform.action!=='drag')||!document.getElementById('set_smart_guides').checked){clear();return;}
        if(!session||session.target!==obj)begin(obj);if(!session)return;
        if(e.e.altKey){session.held={};overlay.style.display='none';return;}
        const rect=canvas.upperCanvasEl.getBoundingClientRect(),v=canvas.viewportTransform;
        const cssX=rect.width/canvas.width||1,cssY=rect.height/canvas.height||1;
        const scaleX=cssX*Math.hypot(v[0],v[1]),scaleY=cssY*Math.hypot(v[2],v[3]);
        const tolerance=Math.max(2,Math.min(12,Number(document.getElementById('set_smart_guide_distance').value)||6));
        const b=bounds(obj),x=match('x',values(b,'x'),tolerance/scaleX),y=match('y',values(b,'y'),tolerance/scaleY);
        session.held={x:obj.lockMovementX?null:x,y:obj.lockMovementY?null:y};
        obj.set({left:obj.left+(session.held.x?.delta||0),top:obj.top+(session.held.y?.delta||0)});obj.setCoords();
        overlay.setAttribute('viewBox',`0 0 ${canvas.width} ${canvas.height}`);
        overlay.style.display=(session.held.x||session.held.y)?'block':'none';
        ['x','y'].forEach((axis,i)=>{
            const hit=session.held[axis],line=lines[i];line.style.display=hit?'':'none';if(!hit)return;
            const a=axis==='x'?{x:hit.value,y:0}:{x:0,y:hit.value};
            const b=axis==='x'?{x:hit.value,y:canvas.height}:{x:canvas.width,y:hit.value};
            const p=fabric.util.transformPoint(a,v),q=fabric.util.transformPoint(b,v);
            for(const [name,value] of Object.entries({x1:p.x,y1:p.y,x2:q.x,y2:q.y}))line.setAttribute(name,value);
            line.setAttribute('stroke-width',1/(axis==='x'?cssX:cssY));
            line.setAttribute('stroke-dasharray',`${4/Math.max(cssX,cssY)} ${3/Math.max(cssX,cssY)}`);
        });
    });
    for(const event of ['mouse:up','object:modified','selection:cleared','canvas:cleared'])canvas.on(event,clear);
    window.addEventListener('mouseup',clear);window.addEventListener('blur',clear);
    document.addEventListener('keydown',e=>{if(e.key==='Alt'){if(session)session.held={};overlay.style.display='none';}if(e.key==='Escape')clear();});
    document.getElementById('set_smart_guides').addEventListener('change',clear);
    return {clear};
};
