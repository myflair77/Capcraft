window.prepareSelectionScene = function() {
    activeTool=null;canvas.isDrawingMode=false;
    commitLoadToCanvas(null,1000,650,'#eef4fa');
    for(let i=0;i<5;i++) {
        canvas.add(new fabric.Rect({id:`selection-${i+1}`,left:65+i*185,top:260,width:120,height:120,
            fill:['#e75656','#3aaf67','#437ee5','#e4a438','#9661c9'][i]}));
        canvas.add(new fabric.Text(String(i+1),{left:110+i*185,top:210,fontSize:32,selectable:false,evented:false}));
    }
    canvas.discardActiveObject();canvas.renderAll();
    window.selectionTrace=[];
    canvas.on('mouse:down',e=>{
        const row={clicked:e.target?.id,selected:canvas.getActiveObject()?.id,x:e.e.clientX,y:e.e.clientY};
        selectionTrace.push(row);console.log('SELECTION_TRACE '+JSON.stringify(row));
    });
    canvas.on('after:render',e=>{
        if(e.ctx===canvas.contextContainer) console.log('SELECTION_PAINT '+canvas.getActiveObject()?.id);
    });
};
