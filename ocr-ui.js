/* OCR uses original capture bytes only; never uploads or rasterizes the edited canvas. */
(() => {
    const pending = new Map();
    let dialogItem = null;
    const nativeItems=new Map();
    const languageSelect=document.createElement('select');
    languageSelect.id='ocr_language';languageSelect.title='OCR 인식 언어';
    languageSelect.style.cssText='width:100%;margin:4px 0 8px;padding:4px;border:1px solid #cbd5e1;border-radius:4px';
    for(const [code,label] of Object.entries({auto:'OCR: 자동 판별 (10개 언어·한자)',ko:'한국어',hanja:'한자',en:'영어',es:'스페인어',de:'독일어',fr:'프랑스어',it:'이탈리아어',ru:'러시아어',zh:'중국어',ja:'일본어',th:'태국어'})) {
        const option=document.createElement('option');option.value=code;option.textContent=label;languageSelect.appendChild(option);
    }
    document.getElementById('recent_list_container').before(languageSelect);
    const dialog = document.createElement('dialog');
    dialog.id = 'ocr_dialog';
    dialog.innerHTML = `<h3>인식한 텍스트 <small>PC 내부 처리 · 원본 캡처 기준</small></h3>
        <p id="ocr_status"></p><textarea id="ocr_text" readonly aria-label="인식한 텍스트" spellcheck="false"></textarea>
        <div class="ocr-actions"><button id="ocr_retry">다시 인식</button><button id="ocr_copy">텍스트를 복사</button><button id="ocr_close">닫기</button></div>`;
    document.body.appendChild(dialog);
    const style = document.createElement('style');
    style.textContent = `.btn-ocr{position:absolute;left:6px;bottom:6px;z-index:2;border:1px solid #94a3b8;border-radius:4px;background:#f1f5f9;color:#64748b;font-size:11px;padding:3px 7px;cursor:pointer}
    .btn-ocr.ready{background:#2563eb;color:white;border-color:#2563eb}.btn-ocr:disabled{cursor:wait;opacity:.7}
    #ocr_dialog{width:min(720px,85vw);border:1px solid #94a3b8;border-radius:12px;padding:20px;color:#1e293b;background:#fff}
    #ocr_dialog::backdrop{background:#0006}#ocr_dialog h3{margin:0 0 12px}#ocr_dialog small{font-size:12px;color:#64748b}
    #ocr_status{font-size:13px}#ocr_text{box-sizing:border-box;width:100%;height:48vh;resize:vertical;user-select:text;font:15px/1.65 sans-serif;padding:12px;color:#111827;background:white;border:1px solid #cbd5e1;border-radius:6px}
    .ocr-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}.ocr-actions button{padding:7px 14px;cursor:pointer}`;
    document.head.appendChild(style);

    function source(item) {
        if (item.bgSrc) return item.bgSrc;
        try { return JSON.parse(item.json).backgroundImage?.src || ''; } catch { return ''; }
    }
    async function digest(value) {
        const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
        return Array.from(new Uint8Array(bytes), x=>x.toString(16).padStart(2,'0')).join('');
    }
    function openResult(item) {
        if(window.pyBackend?.open_ocr_result) {
            item._ocrWindowKey ||= crypto.randomUUID();
            nativeItems.set(item._ocrWindowKey,item);
            window.pyBackend.open_ocr_result(item._ocrWindowKey,JSON.stringify(item.ocr));
            return;
        }
        dialogItem = item;
        document.getElementById('ocr_text').value = item.ocr.text;
        document.getElementById('ocr_status').textContent = item.ocr.text
            ? `인식 완료 · ${item.ocr.elapsed}초${item.ocr.lowConfidence ? ' · 확신도가 낮은 '+item.ocr.lowConfidence+'개 영역은 원본과 대조해 주세요.' : ' · 중요한 숫자와 문구는 원본과 대조해 주세요.'}`
            : '인식된 텍스트가 없습니다. 원본 해상도나 글자 방향을 확인해 주세요.';
        if (!dialog.open) dialog.showModal();
    }
    async function recognize(item, force=false, language=languageSelect.value) {
        if (item._ocrBusy) return;
        const src = source(item);
        if (!src.startsWith('data:image/')) { showToast('원본 캡처 이미지가 없어 OCR을 실행할 수 없습니다.'); return; }
        item._ocrBusy = true;
        renderRecentList(false);
        try {
            const hash = await digest(src);
            if (!recentList.includes(item)) { item._ocrBusy=false; return; }
            if (!force && item.ocr?.sourceHash===hash) {
                item._ocrBusy=false;renderRecentList(false);openResult(item);return;
            }
            const backend = window.pyBackend;
            if (!backend?.recognize_text) throw Error('OCR은 Python으로 실행한 프로그램에서 사용할 수 있습니다.');
            const token=crypto.randomUUID();
            pending.set(token,{item,src,hash});
            if(backend.recognize_text_language) backend.recognize_text_language(token,src,language);
            else backend.recognize_text(token,src);
        } catch(error) {
            item._ocrBusy=false;renderRecentList(false);showToast(error.message);
        }
    }
    window.receiveOCRResult = (token, payload) => {
        const job=pending.get(token);
        if (!job) return;
        pending.delete(token);
        const {item,src,hash}=job;
        item._ocrBusy=false;
        if (!recentList.includes(item) || source(item)!==src) return;
        try {
            const result=JSON.parse(payload);
            if (result.error) throw Error(result.error);
            if (typeof result.text!=='string') throw Error('OCR 결과 형식이 올바르지 않습니다.');
            item.ocr={...result, sourceHash:hash};
            if(item._ocrWindowKey && nativeItems.has(item._ocrWindowKey)) openResult(item);
            triggerHistorySave();
            showToast(result.text ? 'OCR 완료: 파란 OCR 버튼을 누르면 텍스트가 열립니다.' : '인식된 텍스트가 없습니다. OCR 버튼에서 결과를 확인해 주세요.');
        } catch(error) { showToast(error.message); }
        renderRecentList(false);
    };
    window.appendOCRButton = (container,item) => {
        const button=document.createElement('button');
        button.className='btn-ocr'+(item.ocr?' ready':'');
        button.textContent=item._ocrBusy?'인식 중…':'OCR';
        button.disabled=!!item._ocrBusy;
        button.title=item.ocr?'인식한 텍스트 보기':'PC 내부에서 원본 캡처(도형·모자이크 편집 전)의 텍스트 인식';
        button.onclick=e=>{e.stopPropagation();recognize(item);};
        button.ondblclick=e=>e.stopPropagation();
        container.appendChild(button);
    };
    window.pruneOCRJobs = () => {
        for(const [key,item] of nativeItems) if(!recentList.includes(item)) {
            window.pyBackend?.close_ocr_result?.(key);nativeItems.delete(key);
        }
        for (const [token,job] of pending) if (!recentList.includes(job.item)) pending.delete(token);
        if (dialogItem && !recentList.includes(dialogItem)) {dialog.close();dialogItem=null;document.getElementById('ocr_text').value='';}
    };
    window.invalidateOCRSource = (item,newSource) => {
        if (source(item)===(newSource || '')) return;
        delete item.ocr;
        if(item._ocrWindowKey) {window.pyBackend?.close_ocr_result?.(item._ocrWindowKey);nativeItems.delete(item._ocrWindowKey);}
        item._ocrBusy=false;
        for(const [token,job] of pending) if(job.item===item) pending.delete(token);
        if(dialogItem===item) {dialog.close();dialogItem=null;document.getElementById('ocr_text').value='';}
    };
    document.getElementById('ocr_close').onclick=()=>dialog.close();
    window.retryNativeOCR=(key,language)=>{
        const item=nativeItems.get(key);if(item&&recentList.includes(item))recognize(item,true,language);
    };
    window.receiveOCRFormatted=(key,payload)=>{
        const item=nativeItems.get(key);if(!item?.ocr||!recentList.includes(item))return;
        try {const data=JSON.parse(payload);if(typeof data.formattedText==='string') {Object.assign(item.ocr,data);triggerHistorySave();}} catch {}
    };
    document.getElementById('ocr_retry').onclick=()=>{const item=dialogItem;dialog.close();if(item)recognize(item,true);};
    document.getElementById('ocr_copy').onclick=async()=>{
        const text=document.getElementById('ocr_text').value;
        try {
            if(window.pyBackend?.copy_text) window.pyBackend.copy_text(text,ok=>showToast(ok?'텍스트를 복사했습니다.':'복사에 실패했습니다.'));
            else {await navigator.clipboard.writeText(text);showToast('텍스트를 복사했습니다.');}
        } catch {showToast('복사에 실패했습니다. 텍스트를 선택해 Ctrl+C로 복사해 주세요.');}
    };
})();
