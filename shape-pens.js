/* Shape outlines retain native Fabric geometry, fills and endpoint controls. */
(() => {
    const kinds=['ballpoint','highlighter','pencil','brush','charcoal'];
    function apply(obj,kind,density){
        if(!kinds.includes(kind))kind='ballpoint';
        const value=density??(kind==='highlighter'?Number(document.getElementById('set_pen_highlighter_opacity').value):
            kind==='ballpoint'?100:Number(document.getElementById('set_pen_'+kind+'_opacity').value));
        obj.set({shapePen:kind,shapeDensity:value,dirty:true});
        if(obj.type==='group')obj.getObjects().forEach(child=>apply(child,kind,value));
    }
    const originalObject=fabric.Object.prototype.toObject;
    fabric.Object.prototype.toObject=function(properties){return originalObject.call(this,['shapePen','shapeDensity'].concat(properties||[]));};
    function color(obj,value){
        const base=NaturalPens.densityBase[obj.shapePen]||100;
        const c=new fabric.Color(value||'transparent');
        return c.setAlpha(c.getAlpha()*Math.min(1,(obj.shapeDensity??base)/base)).toRgba();
    }
    function points(obj){
        const w=obj.width/2,h=obj.height/2;
        if(obj.type==='rect')return [{x:-w,y:-h},{x:w,y:-h},{x:w,y:h},{x:-w,y:h},{x:-w,y:-h}];
        if(obj.type==='ellipse')return Array.from({length:129},(_,i)=>({x:obj.rx*Math.cos(i*Math.PI/64),y:obj.ry*Math.sin(i*Math.PI/64)}));
        const pts=obj.points.map(p=>({x:p.x-obj.pathOffset.x,y:p.y-obj.pathOffset.y}));return [...pts,pts[0]];
    }
    function texture(obj){
        const pts=points(obj),key=JSON.stringify([pts,obj.shapePen,obj.shapeDensity,obj.strokeWidth,obj.strokeDashArray]);
        if(obj._shapeTexture?.key!==key){const d=NaturalPens.geometry(pts,obj.shapePen,obj.strokeWidth,obj.strokeDashArray,{x:0,y:0},obj.shapeDensity);obj._shapeTexture={key,d,path:new Path2D(d)};}
        return obj._shapeTexture;
    }
    function head(obj){
        if(!obj.isArrowHead||!['pencil','charcoal'].includes(obj.shapePen))return null;
        const pts=obj.type==='path'?NaturalPens.pointsFromPath(obj.path).map(p=>({x:p.x-obj.pathOffset.x,y:p.y-obj.pathOffset.y})):points(obj);
        const d=pts.map((p,i)=>`${i?'L':'M'}${p.x} ${p.y}`).join(' ');
        return NaturalPens.headTexture(obj,d,obj.shapePen,obj.shapeDensity,!obj.fill||new fabric.Color(obj.fill).getAlpha()===0);
    }
    for(const Class of [fabric.Rect,fabric.Ellipse,fabric.Polygon,fabric.Path]){
        const render=Class.prototype._render,svg=Class.prototype._toSVG;
        function withStyle(obj,callback){
            const saved={stroke:obj.stroke,fill:obj.fill,naturalPen:obj.naturalPen,naturalDensity:obj.naturalDensity};
            obj.stroke=color(obj,obj.stroke);
            if(obj.isArrowHead&&obj.fill&&new fabric.Color(obj.fill).getAlpha()>0)obj.fill=color(obj,obj.fill);
            if(obj.type==='path'&&!obj.isArrowHead&&NaturalPens.kinds.includes(obj.shapePen)){obj.naturalPen=obj.shapePen;obj.naturalDensity=obj.shapeDensity;}
            try{return callback();}finally{Object.assign(obj,saved);}
        }
        Class.prototype._render=function(ctx){
            if(!this.shapePen||this.shapePen==='ballpoint')return render.call(this,ctx);
            return withStyle(this,()=>{
                const grain=head(this);
                if(grain){ctx.fillStyle=this.fill&&new fabric.Color(this.fill).getAlpha()>0?this.fill:this.stroke;ctx.fill(grain.path);return;}
                if(this.type==='path'||this.shapePen==='highlighter')return render.call(this,ctx);
                const stroke=this.stroke;this.stroke=null;
                try{render.call(this,ctx);}finally{this.stroke=stroke;}
                ctx.fillStyle=stroke;ctx.fill(texture(this).path);
            });
        };
        Class.prototype._toSVG=function(){
            if(!this.shapePen||this.shapePen==='ballpoint')return svg.call(this);
            return withStyle(this,()=>{
                const grain=head(this);
                if(grain){const transform=this.type==='path'?`translate(${this.pathOffset.x} ${this.pathOffset.y})`:'';return ['<g ','COMMON_PARTS','><path transform="',transform,'" style="stroke:none;fill:',this.fill&&new fabric.Color(this.fill).getAlpha()>0?this.fill:this.stroke,'" d="',grain.d,'" /></g>'];}
                // Explicit nested styles survive restoration before Fabric builds
                // the outer SVG style attributes.
                if(this.type==='path'&&NaturalPens.kinds.includes(this.shapePen)&&!this.isArrowHead)return svg.call(this);
                const base=svg.call(this).join('').replace('COMMON_PARTS','style="stroke:'+this.stroke+';fill:'+new fabric.Color(this.fill||'transparent').toRgba()+'"');
                if(this.shapePen==='highlighter'||this.isArrowHead)return ['<g ','COMMON_PARTS','>',base,'</g>'];
                const fillOnly=svg.call(this).join('').replace('COMMON_PARTS','style="stroke:none;fill:'+new fabric.Color(this.fill||'transparent').toRgba()+'"');
                return ['<g ','COMMON_PARTS','>',fillOnly,'<path style="stroke:none;fill:',this.stroke,'" d="',texture(this).d,'" /></g>'];
            });
        };
    }
    window.ShapePens={apply,kinds,points};
})();
