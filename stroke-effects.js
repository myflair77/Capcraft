/* Non-destructive outline effects; stored centerlines keep their connections. */
(() => {
    const row=document.createElement('div');row.style.cssText='display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:10px;';
    row.innerHTML='<label>점선 빈도: <select id="set_dash_frequency" style="width:auto;min-width:0;padding:6px 2px;"><option value="low">낮음</option><option value="medium" selected>중간</option><option value="high">높음</option></select></label><label>물결 높이: <input id="set_wave_height" type="number" min="1" max="30" value="4" style="width:55px;"> px</label><label>물결 간격: <input id="set_wave_spacing" type="number" min="6" max="150" value="40" style="width:55px;"> px</label>';
    document.getElementById('set_pen_bg_color').parentElement.after(row);
    const dash=width=>{const factor={low:5,medium:3,high:1.5}[document.getElementById('set_dash_frequency').value]||3;return [width*factor,width*factor];};
    function wave(points,height,spacing){
        if(points.length<2)return points;
        const cumulative=[0];for(let i=1;i<points.length;i++)cumulative.push(cumulative.at(-1)+Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y));
        const total=cumulative.at(-1);if(!total)return points;
        const closed=Math.hypot(points[0].x-points.at(-1).x,points[0].y-points.at(-1).y)<.01;
        const period=closed?total/Math.max(1,Math.round(total/spacing)):spacing;
        const count=Math.min(5000,Math.max(2,Math.ceil(total/Math.min(2,period/12))));
        const result=[];let segment=1;
        for(let i=0;i<=count;i++){
            const distance=total*i/count;while(segment<points.length-1&&cumulative[segment]<distance)segment++;
            const a=points[segment-1],b=points[segment],length=cumulative[segment]-cumulative[segment-1]||1,t=(distance-cumulative[segment-1])/length;
            const envelope=closed?1:Math.sin(Math.min(1,distance/(period*.4),(total-distance)/(period*.4))*Math.PI/2)**2;
            const offset=height*Math.sin(distance*Math.PI*2/period)*envelope;
            result.push({x:a.x+(b.x-a.x)*t-(b.y-a.y)/length*offset,y:a.y+(b.y-a.y)*t+(b.x-a.x)/length*offset});
        }
        result[0]={...points[0]};result[result.length-1]={...points.at(-1)};return result;
    }
    const pathString=points=>points.map((p,i)=>`${i?'L':'M'} ${p.x} ${p.y}`).join(' ');
    function apply(obj,enabled){
        obj.set({waveLine:!!enabled,waveHeight:Math.max(1,Math.min(30,Number(document.getElementById('set_wave_height').value)||4)),waveSpacing:Math.max(6,Math.min(150,Number(document.getElementById('set_wave_spacing').value)||40)),dirty:true});
        if(obj.type==='group')obj.getObjects().forEach(child=>{if(!child.isArrowHead)apply(child,enabled);});
    }
    const originalObject=fabric.Object.prototype.toObject;
    fabric.Object.prototype.toObject=function(props){return originalObject.call(this,['waveLine','waveHeight','waveSpacing'].concat(props||[]));};
    function proxy(obj){
        const points=obj.type==='path'?NaturalPens.pointsFromPath(obj.path).map(p=>({x:p.x-obj.pathOffset.x,y:p.y-obj.pathOffset.y})):ShapePens.points(obj);
        const key=JSON.stringify([points,obj.waveHeight,obj.waveSpacing,obj.stroke,obj.strokeWidth,obj.strokeDashArray,obj.naturalPen,obj.naturalDensity,obj.shapePen,obj.shapeDensity]);
        if(obj._waveProxy?.key!==key){
            const p=new fabric.Path(pathString(wave(points,obj.waveHeight||4,obj.waveSpacing||40)),{stroke:obj.stroke,strokeWidth:obj.strokeWidth,strokeDashArray:obj.strokeDashArray,fill:null,strokeLineCap:'round',strokeLineJoin:'round',naturalPen:obj.naturalPen,naturalDensity:obj.naturalDensity,shapePen:obj.shapePen,shapeDensity:obj.shapeDensity});
            p.pathOffset={x:0,y:0};obj._waveProxy={key,p};
        }
        return obj._waveProxy.p;
    }
    for(const Class of [fabric.Path,fabric.Rect,fabric.Ellipse,fabric.Polygon]){
        const render=Class.prototype._render,svg=Class.prototype._toSVG,cache=Class.prototype._getCacheCanvasDimensions;
        Class.prototype._getCacheCanvasDimensions=function(){const result=cache.call(this);if(this.waveLine){const h=(this.waveHeight||4)*2;result.width+=h*result.zoomX;result.height+=h*result.zoomY;result.x+=h*result.zoomX;result.y+=h*result.zoomY;}return result;};
        Class.prototype._render=function(ctx){
            if(!this.waveLine||this.isArrowHead)return render.call(this,ctx);
            const stroke=this.stroke,arrow=this.penArrow;this.stroke=null;this.penArrow=false;
            // Draw the native interior only. Outlines are drawn by a cached proxy.
            const natural=this.naturalPen,shape=this.shapePen;this.naturalPen=null;this.shapePen=null;
            try{render.call(this,ctx);}finally{this.stroke=stroke;this.penArrow=arrow;this.naturalPen=natural;this.shapePen=shape;}
            proxy(this)._render(ctx);
            if(arrow){ctx.save();ctx.fillStyle=ctx.strokeStyle=stroke;ctx.lineWidth=this.strokeWidth;ctx.lineCap='round';ctx.lineJoin='round';ctx.setLineDash([]);const grain=NaturalPens.headTexture(this,NaturalPens.arrowData(this),natural,this.naturalDensity,this.penArrowType==='open');const p=grain?grain.path:new Path2D(NaturalPens.arrowData(this));this.penArrowType==='open'&&!grain?ctx.stroke(p):ctx.fill(p);ctx.restore();}
        };
        Class.prototype._toSVG=function(){
            if(!this.waveLine||this.isArrowHead)return svg.call(this);
            const saved={shapePen:this.shapePen,naturalPen:this.naturalPen,penArrow:this.penArrow};
            this.shapePen=null;this.naturalPen=null;this.penArrow=false;
            let fill;
            try{fill=svg.call(this).join('').replace('COMMON_PARTS','style="stroke:none;fill:'+new fabric.Color(this.fill||'transparent').toRgba()+'"');}
            finally{Object.assign(this,saved);}
            const p=proxy(this);let outline=p._toSVG().join('').replace('COMMON_PARTS','style="'+p.getSvgStyles()+'"');
            if(this.penArrow){
                const grain=NaturalPens.headTexture(this,NaturalPens.arrowData(this),this.naturalPen,this.naturalDensity,this.penArrowType==='open');
                const color=new fabric.Color(this.stroke||'#444').toRgba();
                const style=this.penArrowType==='open'&&!grain?`fill:none;stroke:${color};stroke-width:${this.strokeWidth};stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:none`:`stroke:none;fill:${color}`;
                outline+=`<path style="${style}" d="${grain?grain.d:NaturalPens.arrowData(this)}" />`;
            }
            if(this.type==='path')outline=`<g transform="translate(${this.pathOffset.x} ${this.pathOffset.y})">${outline}</g>`;
            return ['<g ','COMMON_PARTS','>',fill,outline,'</g>'];
        };
    }
    const pencilCreate=fabric.PencilBrush.prototype.createPath,pencilRender=fabric.PencilBrush.prototype._render,full=fabric.PencilBrush.prototype.needsFullRender;
    fabric.PencilBrush.prototype.createPath=function(path){const obj=pencilCreate.call(this,path);if(this.waveLine)apply(obj,true);return obj;};
    fabric.PencilBrush.prototype.needsFullRender=function(){return this.waveLine||full.call(this);};
    function preview(original){return function(){if(!this.waveLine)return original.call(this);const points=wave(this._points,Number(document.getElementById('set_wave_height').value)||4,Number(document.getElementById('set_wave_spacing').value)||40);const ctx=this.canvas.contextTop;this._saveAndTransform(ctx);if(this.kind){ctx.fillStyle=this.color;ctx.fill(new Path2D(NaturalPens.geometry(points,this.kind,this.width,this.strokeDashArray,{x:0,y:0},this.density)));}else{ctx.strokeStyle=this.color;ctx.lineWidth=this.width;ctx.lineCap='round';ctx.lineJoin='round';ctx.setLineDash(this.strokeDashArray||[]);ctx.stroke(new Path2D(pathString(points)));}ctx.restore();};}
    fabric.PencilBrush.prototype._render=preview(pencilRender);
    NaturalPens.Brush.prototype._render=preview(NaturalPens.Brush.prototype._render);
    window.StrokeEffects={dash,wave,apply};
})();
