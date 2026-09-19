window.prepareRecentScene = function() {
    recentList = ['#dcecff', '#ffead8', '#dff4e4'].map((color, i) => {
        const label = new fabric.Text(`TEST ${i+1} - recent switching`, {left:80,top:90,fontSize:40,fill:'#24354a'});
        const shape = new fabric.Rect({left:160,top:230,width:220,height:150,fill:['#347bd4','#e3782d','#26965d'][i]});
        const thumb=document.createElement('canvas');thumb.width=200;thumb.height=125;
        const c=thumb.getContext('2d');c.fillStyle=color;c.fillRect(0,0,200,125);
        c.fillStyle='#24354a';c.font='bold 28px sans-serif';c.fillText(`TEST ${i+1}`,40,70);
        return {json:JSON.stringify({objects:[label.toObject(),shape.toObject()]}),thumb:thumb.toDataURL(),width:1000,height:650,bgColor:color};
    });
    activeRecentIdx=-1;hasActiveCanvas=false;
    renderRecentList(false);loadRecentItem(0);
};
