/* Deterministic vector textures: one Fabric path per stroke, no particle objects. */
(() => {
    const kinds = ['pencil', 'brush', 'charcoal'];
    const densityBase={pencil:50,brush:100,charcoal:70};
    const defaults = {pencil:{width:4,color:'#444444',opacity:50},brush:{width:16,color:'#222222',opacity:100},charcoal:{width:22,color:'#444444',opacity:70}};
    function readSettings(){
        for(const kind of kinds){
            const preset=defaults[kind],prefix='set_pen_'+kind;
            preset.width=Math.max(1,Math.min(100,Number(document.getElementById(prefix+'_weight').value)||1));
            preset.opacity=Math.max(0,Math.min(100,Number(document.getElementById(prefix+'_opacity').value)));
            preset.color=new fabric.Color(document.getElementById(prefix+'_color').style.backgroundColor).setAlpha(Math.min(1,preset.opacity/densityBase[kind])).toRgba();
        }
    }
    const backgroundRow=document.getElementById('set_pen_bg_color').parentElement;
    for(const [kind,label] of [['pencil','연필'],['brush','붓'],['charcoal','목탄']]){
        const row=document.createElement('div');row.style.cssText='display:flex;align-items:center;gap:10px;margin-bottom:8px;';
        row.innerHTML=`<span>${label} 선 굵기:</span><input type="number" id="set_pen_${kind}_weight" value="${defaults[kind].width}" min="1" max="100" style="width:50px;"><span>${label} 색상:</span><div id="set_pen_${kind}_color" class="color-btn" style="background-color:${defaults[kind].color}"></div><span>${label} 색상 농도:</span><input type="number" id="set_pen_${kind}_opacity" value="100" min="0" max="100" style="width:45px;">`;
        backgroundRow.before(row);
        row.querySelector('[id$="_opacity"]').style.width='60px';
        row.querySelector('[id$="_opacity"]').value=defaults[kind].opacity;
    }
    const pointsFromPath = path => {
        const points=[]; let last={x:0,y:0};
        for(const c of path) {
            if(c[0]==='M'||c[0]==='L'){last={x:c[1],y:c[2]};points.push(last);}
            else if(c[0]==='Q'||c[0]==='C') {
                const start=last, cubic=c[0]==='C';
                const end={x:c[c.length-2],y:c[c.length-1]};
                for(let j=1;j<=8;j++) {
                    const t=j/8,u=1-t;
                    points.push(cubic?{x:u*u*u*start.x+3*u*u*t*c[1]+3*u*t*t*c[3]+t*t*t*end.x,y:u*u*u*start.y+3*u*u*t*c[2]+3*u*t*t*c[4]+t*t*t*end.y}:
                        {x:u*u*start.x+2*u*t*c[1]+t*t*end.x,y:u*u*start.y+2*u*t*c[2]+t*t*end.y});
                }
                last=end;
            }
        }
        return points;
    };
    function geometry(points,kind,width,dashed,offset={x:0,y:0},density=densityBase[kind]) {
        if(!points.length)return '';
        width=Math.max(1,Math.min(200,width||1));
        let total=0;const lengths=[0];
        for(let i=1;i<points.length;i++){total+=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y);lengths.push(total);}
        const step=Math.max(kind==='brush'?1:0.8,width*(kind==='charcoal'?.12:.14),total/3500);
        let seed=731,segment=1,d='';
        const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
        const n=v=>Number(v.toFixed(2));
        const dot=(x,y,r)=>{x-=offset.x;y-=offset.y;d+=`M${n(x-r)} ${n(y)}a${n(r)} ${n(r)} 0 1 0 ${n(2*r)} 0a${n(r)} ${n(r)} 0 1 0 ${n(-2*r)} 0z`;};
        for(let distance=0;distance<=total+step/2;distance+=step){
            const at=Math.min(distance,total);
            while(segment<points.length-1&&lengths[segment]<at)segment++;
            const a=points[Math.max(0,segment-1)],b=points[Math.min(segment,points.length-1)];
            const ratio=(at-(lengths[segment-1]||0))/((lengths[segment]||0)-(lengths[segment-1]||0)||1);
            const x=a.x+(b.x-a.x)*ratio,y=a.y+(b.y-a.y)*ratio;
            const dashLength=Array.isArray(dashed)?dashed[0]:width*3;
            if(dashed&&Math.floor(at/Math.max(.1,dashLength))%2)continue;
            if(kind==='brush') {
                const taper=.18+.82*Math.min(1,at/(width*1.5),(total-at)/(width*1.5));
                const radius=width*.48*Math.max(.18,taper)*(0.82+0.18*Math.sin(at/(width*2)));
                dot(x,y,Math.max(.3,radius));
            } else {
                const count=Math.round((kind==='charcoal'?9:4)*Math.max(1,(density??densityBase[kind])/densityBase[kind]));
                for(let j=0;j<count;j++) {
                    const angle=random()*Math.PI*2,r=Math.sqrt(random())*width*.42;
                    dot(x+Math.cos(angle)*r,y+Math.sin(angle)*r,Math.max(.16,width*(kind==='charcoal'?.055:.04)*(0.4+random())));
                }
            }
            if(total===0)break;
        }
        return d;
    }
    const originalRender=fabric.Path.prototype._render, originalSVG=fabric.Path.prototype._toSVG;
    const originalDimensions=fabric.Path.prototype._getNonTransformedDimensions;
    fabric.Path.prototype._getNonTransformedDimensions=function(){
        const dimensions=originalDimensions.call(this);
        if(this.penArrow){const padding=(this.strokeWidth||1)*6+16;dimensions.x+=padding;dimensions.y+=padding;}
        return dimensions;
    };
    function arrowFrame(obj){
        let previous=null,last=null;
        for(const command of obj.path){
            if(!['M','L','Q','C'].includes(command[0]))continue;
            const end={x:command.at(-2),y:command.at(-1)};
            if(command[0]!=='M'&&previous&&Math.hypot(end.x-previous.x,end.y-previous.y)>.1){
                let start=command[0]==='C'?{x:command[3],y:command[4]}:command[0]==='Q'?{x:command[1],y:command[2]}:previous;
                if(Math.hypot(end.x-start.x,end.y-start.y)<.001)start=previous;
                last={end,angle:Math.atan2(end.y-start.y,end.x-start.x)};
            }
            previous=end;
        }
        return last;
    }
    function arrowData(obj){
        const frame=arrowFrame(obj);if(!frame)return '';
        const {end,angle}=frame,w=(obj.strokeWidth||1)*({xs:1.5,s:2,m:3,l:4,xl:5}[obj.penArrowSize]||3)+8;
        const x=end.x-obj.pathOffset.x,y=end.y-obj.pathOffset.y;
        const bx=x-Math.cos(angle)*w,by=y-Math.sin(angle)*w;
        const a=`${bx-Math.sin(angle)*w*.45} ${by+Math.cos(angle)*w*.45}`,b=`${bx+Math.sin(angle)*w*.45} ${by-Math.cos(angle)*w*.45}`;
        if(obj.penArrowType==='open')return `M${a}L${x} ${y}L${b}`;
        const notch=obj.penArrowType==='stealth'?`L${x-Math.cos(angle)*w*.6} ${y-Math.sin(angle)*w*.6}`:'';
        return `M${x} ${y}L${a}${notch}L${b}Z`;
    }
    // Use the same deterministic grain and density as the shaft, including SVG export.
    function headTexture(obj,d,kind,density,open){
        if(!['pencil','charcoal'].includes(kind))return null;
        // Filled heads have strokeWidth=0; grain must use the shaft's width,
        // not a one-pixel outline fallback.
        const width=obj.arrowStrokeWidth||obj.group?.getObjects().find(o=>o.isArrowBody)?.strokeWidth||obj.strokeWidth||1;
        const key=JSON.stringify([d,kind,density,width,open]);
        if(obj._headTexture?.key===key)return obj._headTexture;
        const pts=pointsFromPath(fabric.util.parsePath(d));
        let marks='';
        if(open)marks=geometry(pts,kind,width,false,{x:0,y:0},density);
        else if(pts.length>=3){
            const minX=Math.min(...pts.map(p=>p.x)),maxX=Math.max(...pts.map(p=>p.x));
            const minY=Math.min(...pts.map(p=>p.y)),maxY=Math.max(...pts.map(p=>p.y));
            const radius=Math.max(.16,width*(kind==='charcoal'?.055:.04));
            const step=Math.max(.6,radius*2,Math.sqrt((maxX-minX)*(maxY-minY)/30000));
            let seed=731;
            const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
            const strength=Math.min(2,Math.max(0,(density??densityBase[kind])/densityBase[kind]));
            for(let y=minY;y<=maxY;y+=step)for(let x=minX;x<=maxX;x+=step){
                const px=x+random()*step,py=y+random()*step;
                let inside=false,edge=Infinity;
                for(let i=0,j=pts.length-1;i<pts.length;j=i++){
                    const a=pts[j],b=pts[i],dx=b.x-a.x,dy=b.y-a.y;
                    if((a.y>py)!==(b.y>py)&&px<(b.x-a.x)*(py-a.y)/(b.y-a.y)+a.x)inside=!inside;
                    const t=Math.max(0,Math.min(1,((px-a.x)*dx+(py-a.y)*dy)/(dx*dx+dy*dy||1)));
                    edge=Math.min(edge,Math.hypot(px-a.x-t*dx,py-a.y-t*dy));
                }
                const r=Math.min(edge,radius*(.4+random())*Math.sqrt(strength));
                if(inside&&r>.05){
                    const n=v=>Number(v.toFixed(3));
                    marks+=`M${n(px-r)} ${n(py)}a${n(r)} ${n(r)} 0 1 0 ${n(2*r)} 0a${n(r)} ${n(r)} 0 1 0 ${n(-2*r)} 0z`;
                }
            }
        }
        return obj._headTexture={key,d:marks,path:new Path2D(marks)};
    }
    const originalObject=fabric.Path.prototype.toObject;
    fabric.Path.prototype.toObject=function(properties){return originalObject.call(this,['naturalPen','naturalDensity','penArrow','penArrowType','penArrowSize','arrowStrokeWidth'].concat(properties||[]));};
    function data(obj){
        const key=[obj.strokeWidth,JSON.stringify(obj.strokeDashArray),obj.naturalPen,obj.naturalDensity,obj.pathOffset.x,obj.pathOffset.y].join('|');
        if(!obj._naturalCache||obj._naturalCache.path!==obj.path||obj._naturalCache.key!==key){
            const d=geometry(pointsFromPath(obj.path),obj.naturalPen,obj.strokeWidth,obj.strokeDashArray,obj.pathOffset,obj.naturalDensity);
            obj._naturalCache={key,path:obj.path,d,shape:new Path2D(d)};
        }
        return obj._naturalCache;
    }
    fabric.Path.prototype._render=function(ctx){
        if(!kinds.includes(this.naturalPen))originalRender.call(this,ctx);
        else {
            // Preserve the common closed-stroke background without drawing a
            // solid shaft over the textured pen.
            const stroke=this.stroke;this.stroke=null;originalRender.call(this,ctx);this.stroke=stroke;
            ctx.fillStyle=this.stroke||'#444';ctx.fill(data(this).shape);
        }
        if(this.penArrow){
            ctx.save();const shape=new Path2D(arrowData(this));
            const grain=headTexture(this,arrowData(this),this.naturalPen,this.naturalDensity,this.penArrowType==='open');
            if(grain){ctx.fillStyle=this.stroke||'#444';ctx.fill(grain.path);}
            else if(this.penArrowType==='open'){ctx.strokeStyle=this.stroke||'#444';ctx.lineWidth=this.strokeWidth||1;ctx.setLineDash([]);ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke(shape);}
            else{ctx.fillStyle=this.stroke||'#444';ctx.fill(shape);}ctx.restore();
        }
    };
    fabric.Path.prototype._toSVG=function(){
        const color=new fabric.Color(this.stroke||'#444').toRgba();
        const background=originalSVG.call(this).join('').replace('COMMON_PARTS','style="stroke:none;fill:'+new fabric.Color(this.fill||'transparent').toRgba()+'"');
        // Fabric's SVG wrapper applies -pathOffset to COMMON_PARTS. Texture and
        // head geometry are already local, so cancel that offset for these marks.
        const localTransform=`translate(${this.pathOffset.x} ${this.pathOffset.y})`;
        const markup=kinds.includes(this.naturalPen)?['<g ', 'COMMON_PARTS', '>',background,'<path transform="',localTransform,'" style="stroke:none;fill:',color,'" d="',data(this).d,'" /></g>']:originalSVG.call(this);
        if(this.penArrow){const grain=headTexture(this,arrowData(this),this.naturalPen,this.naturalDensity,this.penArrowType==='open');const style=this.penArrowType==='open'&&!grain?`fill:none;stroke:${color};stroke-width:${this.strokeWidth};stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:none`:`stroke:none;fill:${color}`;markup.push('<path style="',style,'" d="',grain?grain.d:arrowData(this),'" />');}
        return markup;
    };
    const Brush=fabric.util.createClass(fabric.PencilBrush,{
        type:'natural',
        needsFullRender(){return true;},
        createPath(path){const obj=this.callSuper('createPath',path);obj.naturalPen=this.kind;obj.naturalDensity=this.density??densityBase[this.kind];return obj;},
        _render(){
            const ctx=this.canvas.contextTop;this._saveAndTransform(ctx);
            ctx.fillStyle=this.color;
            ctx.fill(new Path2D(geometry(this._points,this.kind,this.width,this.strokeDashArray,{x:0,y:0},this.density)));
            ctx.restore();
        }
    });
    window.NaturalPens={kinds,defaults,Brush,geometry,readSettings,arrowData,arrowFrame,densityBase,pointsFromPath,headTexture};
})();
