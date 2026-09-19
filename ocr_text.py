"""Conservative local OCR paragraph reconstruction. Only whitespace may change."""
import re
import statistics
import sys
from pathlib import Path
from ocr_engine import ROOT

VERSION = 2


def validate_spacing_models(model_path):
    # A failed native Kiwi constructor can corrupt the heap on Windows. Never
    # call it with the removed KnLM model or missing packaged model files.
    required = ('cong.mdl', 'sj.morph', 'default.dict', 'combiningRule.txt')
    missing = [name for name in required if not (Path(model_path) / name).is_file()
               or (Path(model_path) / name).stat().st_size == 0]
    if missing:
        raise RuntimeError('문단 정리 모델 파일이 없거나 비어 있습니다. OCR 구성 요소를 복구해 주세요: ' + ', '.join(missing))


def compact(text):
    return re.sub(r'\s+', '', text)


def paragraphs(result):
    text = result.get('text', '')
    rows = result.get('lines') or []
    # Never rebuild from coordinates unless they correspond exactly to the raw OCR.
    if not rows or compact(''.join(r.get('text','') for r in rows)) != compact(text):
        return [[line.strip() for line in block.splitlines() if line.strip()]
                for block in re.split(r'\n\s*\n', text) if block.strip()]
    if not all(isinstance(r.get('box'),list) and len(r['box'])==4 for r in rows):
        return [[line] for line in text.splitlines() if line.strip()]
    heights = [max(1,r['box'][3]-r['box'][1]) for r in rows]
    h = statistics.median(heights)
    gaps = [b['box'][1]-a['box'][3] for a,b in zip(rows,rows[1:])
            if 0 < b['box'][1]-a['box'][3] < h*1.5]
    gap = statistics.median(gaps) if gaps else h*.4
    blocks=[]
    for i,row in enumerate(rows):
        start=i==0
        if i:
            prev=rows[i-1]['box'];box=row['box']
            separation=box[1]-prev[3]
            # Preserve blank-line paragraphs, columns, table rows and explicit list items.
            start=(separation>max(h*.9,gap*1.8) or box[1]<prev[1]+h*.45
                   or abs(box[0]-prev[0])>max(h*3,(prev[2]-prev[0])*.55)
                   or bool(re.match(r'^(?:[•●▪-]\s|\d+[.)]\s)',row['text'])))
        if start:blocks.append([])
        blocks[-1].append(row['text'].strip())
    return blocks


def punctuation(text):
    # Hangul sentence endings only: do not break decimals, URLs, versions or abbreviations.
    text=re.sub(r'(?<=[가-힣])([.!?])(?=[가-힣A-Z])',r'\1 ',text)
    particles=('은','는','이','가','을','를','의','와','과','도','만','에','로','으로','라고','라는','이라','처럼','부터','까지')
    pattern = r"(?<![A-Za-z])(['\"‘“])([^'\"‘’“”\n]+)(['\"’”])"
    matches=list(re.finditer(pattern,text))
    for match in reversed(matches):
        opening,_,closing=match.groups()
        if {'\'':'\'','"':'"','‘':'’','“':'”'}[opening]!=closing:continue
        start,end=match.span()
        before=' ' if start and re.match(r'[가-힣A-Za-z0-9]',text[start-1]) else ''
        tail=text[end:]
        after=' ' if tail and re.match(r'[가-힣A-Za-z0-9]',tail) and not tail.startswith(particles) else ''
        text=text[:start]+before+text[start:end]+after+tail
    return text


class ParagraphFormatter:
    def __init__(self):
        self.kiwi=None

    def _spacing(self, text):
        if self.kiwi is None:
            deps=ROOT/'.ocr-deps'
            if sys.version_info[:2]==(3,13) and deps.is_dir() and str(deps) not in sys.path:
                sys.path.append(str(deps))
            from kiwipiepy import Kiwi
            from kiwipiepy_model import get_model_path
            model_path = get_model_path()
            validate_spacing_models(model_path)
            self.kiwi=Kiwi(num_workers=1, model_path=model_path, model_type='cong')
        return self.kiwi.space(text,reset_whitespace=False)

    def join(self, lines):
        if not lines:return ''
        # Analyze joined paragraph once. Only adopt spaces at former line boundaries;
        # existing words, names and internal spacing are deliberately preserved.
        candidate=''.join(lines)
        spaced=self._spacing(candidate) if re.search('[가-힣]',candidate) and len(lines)>1 else candidate
        gap_positions=set();count=0
        if compact(candidate)==compact(spaced):
            for char in spaced:
                if char.isspace():gap_positions.add(count)
                else:count+=1
        output=lines[0];offset=len(compact(lines[0]))
        for previous,line in zip(lines,lines[1:]):
            sep=' '
            if previous and line:
                if re.match(r'[가-힣]',previous[-1]) and re.match(r'[가-힣]',line[0]):
                    sep=' ' if offset in gap_positions else ''
                elif re.search(r'\([A-Z0-9]+$',output) and re.match(r'[A-Z0-9]+\)',line):
                    sep=''  # e.g. (R + PG), without joining ordinary English words.
                elif line[0] in ',.;:!?)]}':sep=''
            output+=sep+line;offset+=len(compact(line))
        return punctuation(output)

    def format(self,result):
        raw=result.get('text','')
        if not isinstance(raw,str) or len(raw)>100_000:
            raise ValueError('문단 정리는 10만 자 이하의 OCR 텍스트를 지원합니다.')
        formatted='\n\n'.join(self.join(block) for block in paragraphs(result))
        if compact(raw)!=compact(formatted):
            raise ValueError('원문 문자 보존 검사에 실패했습니다. 원문을 사용해 주세요.')
        return {'formattedText':formatted,'formatVersion':VERSION,
                'formatNotes':'줄 간격과 로컬 한국어 분석으로 정리했습니다. 고유명사·표·다단 문서는 원문과 비교해 주세요.'}
