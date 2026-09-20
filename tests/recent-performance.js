(async () => {
    const wait=ms=>new Promise(r=>setTimeout(r,ms));
    const rows=[];
    try {
        for(let n=0;n<600 && (typeof activeRecentIdx==='undefined' || activeRecentIdx<0 || _recentLoading);n++) await wait(50);
        if(activeRecentIdx<0) throw Error('History not ready');
        await wait(1500);
        let totals={};
        const wrap=(obj,key)=>{const fn=obj[key];obj[key]=function(...args){const t=performance.now();try{return fn.apply(this,args);}finally{totals[key]=(totals[key]||0)+performance.now()-t;}};};
        wrap(window,'saveHistory');wrap(window,'getCanvasJSON');wrap(window,'initHistory');
        wrap(canvas,'setDimensions');wrap(canvas,'renderAll');
        wrap(CapcraftPopout,'drawCachedShadow');wrap(CapcraftPopout,'adopt');wrap(CapcraftPopout,'regenerate');
        const indexes=recentList.length>=5 ? [3,4,3,4] : Array.from({length:Math.min(recentList.length,5)},(_,i)=>i);
        for(let round=0;round<2;round++) for(const idx of indexes) {
            totals={};const t=performance.now();loadRecentItem(idx);
            while(_recentLoading) await wait(5);
            await new Promise(requestAnimationFrame);
            rows.push({name:`recent ${idx} round ${round}`,ok:activeRecentIdx===idx,ms:performance.now()-t,
                width:canvas.width,height:canvas.height,objects:canvas.getObjects().length,parts:{...totals}});
        }
    } catch(e) {rows.push({name:'recent benchmark',ok:false,error:String(e)});}
    console.log(JSON.stringify(rows));window.qtTestResults=JSON.stringify(rows);
})();
