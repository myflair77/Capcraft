"""Recover omitted Han glyphs from spatial gaps, preserving Korean text."""
import re
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
SCRIPTS = {
    'rec': re.compile('[가-힣]'),
    'cjk': re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaffぁ-ヿ]'),
    'latin': re.compile('[A-Za-zÀ-ž]'),
    'ru': re.compile('[Ѐ-ӿ]'),
    'th': re.compile('[\u0e00-\u0e7f]'),
}

def positioned_chars(text, info, width):
    """CTC columns are comparable only after normalizing each model's time axis."""
    chars=[c for word in info.words for c in word]
    cols=[x for word in info.word_cols for x in word]
    indices=[i for i,c in enumerate(text) if not c.isspace()]
    if len(indices)!=len(chars) or not info.line_txt_len:
        return []
    return [(c,x*width/info.line_txt_len,i) for c,x,i in zip(chars,cols,indices)]

def choose_local(rows, base_group):
    """Never fill a missing region with a model's punctuation-only hallucination."""
    valid=[r for r in rows if r[1]>=.65 and SCRIPTS[r[2]].search(r[0])
           and r[2]!=base_group]
    return max(valid,key=lambda r:r[1]) if valid else None

def script_replacements(crop, text, aligned, all_positions, recognizer, diagnostics=None):
    """Resolve Cyrillic/Latin lookalikes using aligned evidence, not spelling guesses."""
    import cv2
    import numpy as np
    from rapidocr.ch_ppocr_rec import TextRecInput
    edits=[]
    height,width=crop.shape[:2]
    background=tuple(int(v) for v in np.median(crop.reshape(-1,3),axis=0))
    for group in ['ru','th','cjk']:
        if group not in all_positions:continue
        other,info=all_positions[group]
        points=positioned_chars(other,info,width)
        run=[]
        separated=[]
        for point in points:
            if separated and point[2]>separated[-1][2]+1:
                separated.append(('',point[1],point[2]-1))
            separated.append(point)
        for item in separated+[('',width+height,len(other))]:
            if SCRIPTS[group].fullmatch(item[0]):
                run.append(item);continue
            if len(run)>=2:
                left=max(0,int(run[0][1]-height*.5));right=min(width,int(run[-1][1]+height*.6))
                covered=[p for p in aligned if left<=p[1]<=right]
                if covered:
                    begin,end=covered[0][2],covered[-1][2]+1
                    old=text[begin:end]
                    # Preserve real Hangul/numbers. Only a Latin-lookalike span
                    # supported by another native-script model is eligible.
                    if re.fullmatch('[A-Za-z ]{2,}',old):
                        piece=cv2.copyMakeBorder(crop[:,left:right],4,4,6,6,cv2.BORDER_CONSTANT,value=background)
                        out=recognizer(group)(TextRecInput(img=[piece,cv2.resize(piece,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)]))
                        values=[v.strip() for v in out.txts]
                        expected=''.join(p[0] for p in run)
                        if values[0]==values[1]==expected and min(out.scores)>=.85:
                            edits.append((begin,end,expected,float(min(out.scores))))
                        elif diagnostics is not None:
                            diagnostics.append({'offset':begin,'candidate':old,'alternative':expected,'reason':'문자 체계 판별 불일치'})
            run=[]
    accepted=[]
    for edit in sorted(edits,key=lambda e:e[3],reverse=True):
        if not any(edit[0]<other[1] and other[0]<edit[1] for other in accepted):
            accepted.append(edit)
    return accepted

def mixed_line(crop, choices, recognizer, positions=None, groups=None, diagnostics=None):
    from ocr_languages import choose_candidate
    base=choose_candidate(choices)
    if not base[0].strip():return None
    base_group=base[2]
    groups=groups or [r[2] for r in choices]
    import cv2
    import numpy as np
    from rapidocr.ch_ppocr_rec import TextRecInput
    all_positions=positions if isinstance(positions,dict) else {}
    if isinstance(positions,dict):
        positions=positions.get(base_group)
    if positions is None:
        output=recognizer(base_group)(TextRecInput(img=[crop],return_word_box=True))
        positions=(output.txts[0],output.word_results[0])
    text,info=positions
    height,width=crop.shape[:2]
    aligned=positioned_chars(text,info,width)
    if not aligned:return None
    replacements=script_replacements(crop,text,aligned,all_positions,recognizer,diagnostics)
    background=tuple(int(v) for v in np.median(crop.reshape(-1,3),axis=0))
    pieces=[];locations=[]
    boundaries=[('',-height*.5,-1)]+aligned+[('',width+height*.5,len(text))]
    for (a,x,_),(b,y,index) in zip(boundaries,boundaries[1:]):
        if y-x<height*1.65:continue
        left=max(0,int(x+height*(.18 if a in "([·" and a else .5)))
        right=min(width,int(y-height*(.12 if b in ")]·" and b else .45)))
        if right-left<height*.5:continue
        region=crop[:,left:right]
        if float(np.std(cv2.cvtColor(region,cv2.COLOR_BGR2GRAY)))<15:continue
        pieces.append(cv2.copyMakeBorder(region,4,4,6,6,cv2.BORDER_CONSTANT,value=background))
        locations.append(index)
        if len(pieces)>=12:break
    if not pieces:
        if not replacements:return None
        for begin,end,value,_ in sorted(replacements,reverse=True):text=text[:begin]+value+text[end:]
        return text,min([base[1]]+[r[3] for r in replacements]),'mixed'
    local=[[] for _ in pieces]
    for group in groups:
        if group==base_group:continue
        output=recognizer(group)(TextRecInput(img=pieces))
        for rows,value,score in zip(local,output.txts,output.scores):
            rows.append((value.strip(),float(score),group))
    inserts=[];scores=[base[1]]
    for piece,location,rows in zip(pieces,locations,local):
        candidate=choose_local(rows,base_group)
        if candidate is None:continue
        value,score,group=candidate
        # Two differently sampled views must agree before accepting uncertain text.
        enlarged=cv2.resize(piece,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
        retry=recognizer(group)(TextRecInput(img=[enlarged]))
        agreement=value==retry.txts[0].strip()
        if not agreement:
            if diagnostics is not None:diagnostics.append({'offset':location,'candidate':value,'alternative':retry.txts[0].strip(),'reason':'부분 재인식 결과 불일치'})
            continue
        inserts.append((location,value));scores.append(min(score,float(retry.scores[0])))
        if diagnostics is not None and min(score,float(retry.scores[0]))<.8:
            diagnostics.append({'offset':location,'candidate':value,'reason':'부분 인식 신뢰도 낮음'})
    if not inserts and not replacements:return None
    edits=replacements+[(location,location,value,1) for location,value in inserts
                        if not any(a<=location<b for a,b,_,_ in replacements)]
    scores.extend(r[3] for r in replacements)
    for begin,end,value,_ in sorted(edits,reverse=True):text=text[:begin]+value+text[end:]
    return text,min(scores),'mixed'
