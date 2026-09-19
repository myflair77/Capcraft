(async()=>{
    const wait=ms=>new Promise(r=>setTimeout(r,ms));
    const check=(ok,msg)=>{if(!ok)throw Error(msg);};
    try {
        for(let i=0;i<100&&!window.pyBackend?.recognize_text;i++)await wait(50);
        const image=document.createElement('canvas');image.width=900;image.height=160;
        const ctx=image.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,900,160);
        ctx.fillStyle='black';ctx.font='26px "Malgun Gothic"';
        ctx.fillText('한글과 English OCR 테스트 12345',24,60);
        const src=image.toDataURL();
        recentList=[{thumb:src,bgSrc:src,json:'{}',width:900,height:160,time:Date.now()}];
        activeRecentIdx=-1;renderRecentList(false);
        let heartbeat=0;
        const timer=setInterval(()=>heartbeat++,20);
        document.querySelector('.btn-ocr').click();
        for(let i=0;i<1200&&!recentList[0].ocr;i++)await wait(50);
        clearInterval(timer);
        const item=recentList[0];
        check(item.ocr,'OCR did not complete');
        check(item.ocr.text.replace(/\s/g,'').includes('한글과EnglishOCR테스트12345'),'Recognition mismatch');
        check(heartbeat>5,'UI heartbeat blocked');
        check(activeRecentIdx===-1,'OCR activated thumbnail');
        check(document.querySelector('.btn-ocr.ready'),'OCR button not activated');
        document.querySelector('.btn-ocr').click();await wait(100);
        check(document.getElementById('ocr_dialog').open,'Result window did not open');
        check(document.getElementById('ocr_text').value===item.ocr.text,'Result text mismatch');
        await new Promise(resolve=>window.pyBackend.copy_text(item.ocr.text,ok=>{check(ok,'Copy failed');resolve();}));
        triggerHistorySave();await wait(1600);
        const saved=await new Promise(resolve=>window.pyBackend.load_history(resolve));
        check(JSON.parse(saved)[0].ocr.text===item.ocr.text,'OCR result not persisted');
        window.qtTestResults=JSON.stringify([{name:'local OCR: real Qt bridge, UI heartbeat, result dialog, copy and persistence',ok:true}]);
    } catch(error) {window.qtTestResults=JSON.stringify([{name:'local OCR end-to-end',ok:false,error:String(error)}]);}
})();
