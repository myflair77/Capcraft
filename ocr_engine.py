"""Local-only Korean/English OCR. No image paths/URLs or network fallback accepted."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import copy
from collections import OrderedDict
from ocr_languages import LANGUAGES, choose_candidate, detect_language, recognition_groups

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


class LocalOCR:
    def __init__(self):
        self.engine = None
        self.recognizers = OrderedDict()

    def initialize(self):
        if self.engine is not None:
            return
        deps = ROOT / '.ocr-deps'
        if sys.version_info[:2] == (3, 13) and deps.is_dir() and str(deps) not in sys.path:
            sys.path.append(str(deps))
        model_root = ROOT / 'models' / 'ocr'
        manifest = json.loads((model_root / 'manifest.json').read_text(encoding='utf-8'))
        paths = {}
        for name, entry in manifest['models'].items():
            path = model_root / entry['file']
            if not path.is_file():
                raise RuntimeError('OCR 모델이 설치되지 않았습니다. scripts/setup_ocr.py를 실행해 주세요.')
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise RuntimeError('OCR 모델 파일 검증에 실패했습니다. 모델을 다시 설치해 주세요.')
            paths[name] = str(path)
        self.model_paths = paths
        try:
            from rapidocr import RapidOCR, OCRVersion, ModelType, LangRec
            from rapidocr.utils.download_file import DownloadFile
            import onnxruntime
            onnxruntime.disable_telemetry_events()
        except ImportError as error:
            raise RuntimeError('로컬 OCR 구성요소가 없습니다. requirements-ocr.txt를 설치해 주세요.') from error

        def no_download(*args, **kwargs):
            raise RuntimeError('OCR 실행 중 네트워크 다운로드는 허용하지 않습니다.')
        # Even missing dictionaries/fonts must never trigger automatic downloads.
        DownloadFile.run = staticmethod(no_download)
        self.engine = RapidOCR(params={
            'Det.model_path': paths['det'], 'Rec.model_path': paths['rec'],
            'Cls.model_path': paths['cls'],
            'Det.ocr_version': OCRVersion.PPOCRV5, 'Det.model_type': ModelType.SERVER,
            'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE,
            'Rec.lang_type': LangRec.KOREAN,
            'Det.mean': [0.485, 0.456, 0.406], 'Det.std': [0.229, 0.224, 0.225],
            'Det.limit_side_len': 1600, 'Det.limit_type': 'max',
            'Global.max_side_len': 1600, 'Global.text_score': 0.35,
            'Global.use_cls': False,
            'Global.log_level': 'error',
            'EngineConfig.onnxruntime.intra_op_num_threads': min(4, max(1, (os.cpu_count() or 2)//2)),
            'EngineConfig.onnxruntime.inter_op_num_threads': 1,
        })

    def recognizer(self, group):
        if group=='rec':return self.engine.text_rec
        if group in self.recognizers:
            self.recognizers.move_to_end(group)
            return self.recognizers[group]
        from rapidocr.ch_ppocr_rec import TextRecognizer
        from rapidocr import LangRec, ModelType
        cfg=copy.deepcopy(self.engine.cfg.Rec)
        cfg.model_path=self.model_paths[group]
        cfg.lang_type={'latin':LangRec.LATIN,'ru':LangRec.ESLAV,'cjk':LangRec.CH,'th':LangRec.TH}[group]
        cfg.model_type=ModelType.SERVER if group=='cjk' else ModelType.MOBILE
        # Bound extra recognizer sessions; detector and the Korean model are shared.
        if len(self.recognizers)>=2:self.recognizers.popitem(last=False)
        self.recognizers[group]=TextRecognizer(cfg)
        return self.recognizers[group]

    def recognize(self, data_url, language='auto'):
        started = time.monotonic()
        if language not in LANGUAGES:raise ValueError('지원하지 않는 OCR 언어입니다.')
        if not isinstance(data_url, str) or not data_url.startswith(('data:image/png;base64,', 'data:image/jpeg;base64,', 'data:image/webp;base64,')):
            raise ValueError('OCR은 로컬 캡처 이미지 데이터만 처리합니다.')
        if len(data_url) > 64 * 1024 * 1024:
            raise ValueError('이미지가 너무 큽니다. 영역을 나누어 캡처해 주세요.')
        raw = base64.b64decode(data_url.split(',', 1)[1], validate=True)
        self.initialize()
        from PIL import Image
        import cv2
        import numpy as np
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('이미지가 너무 큽니다. 영역을 나누어 캡처해 주세요.')
            rgba = image.convert('RGBA')
            white = Image.new('RGBA', rgba.size, 'white')
            white.alpha_composite(rgba)
            pixels = cv2.cvtColor(np.array(white.convert('RGB')), cv2.COLOR_RGB2BGR)
        height, width = pixels.shape[:2]
        lines = []
        from rapidocr.ch_ppocr_rec import TextRecInput
        from rapidocr.utils.process_img import get_rotate_crop_image
        crops=[];boxes=[]
        # Overlapping full-resolution tiles avoid shrinking long captures into unreadable text.
        for y in tile_starts(height):
            for x in tile_starts(width):
                tile = pixels[y:y+1536, x:x+1536]
                result = self.engine(tile,use_rec=False,use_cls=False)
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    crops.append(get_rotate_crop_image(tile,np.array(box).copy()))
                    box = np.asarray(box) + [x, y]
                    bounds = [float(box[:,0].min()), float(box[:,1].min()), float(box[:,0].max()), float(box[:,1].max())]
                    boxes.append(bounds)
        groups=recognition_groups(language)
        candidates=[[] for _ in crops]
        model_positions={}
        if crops:
            for group in groups:
                result=self.recognizer(group)(TextRecInput(img=crops,return_word_box=language in ('auto','ko')))
                for i,(text,score) in enumerate(zip(result.txts,result.scores)):
                    candidates[i].append((text,float(score),group))
                    if language in ('auto','ko'):
                        model_positions.setdefault(i,{})[group]=(text,result.word_results[i])
            for i,(choices,box,crop) in enumerate(zip(candidates,boxes,crops)):
                text,score,group=choose_candidate(choices)
                diagnostics=[]
                if language in ('auto','ko'):
                    from ocr_mixed import mixed_line
                    mixed=mixed_line(crop,choices,self.recognizer,model_positions.get(i),groups,diagnostics)
                    if mixed is not None:
                        text,score,group=mixed
                if score<0.35 or not text.strip():continue
                lines.append({'text':text,'confidence':score,'box':box,'review':diagnostics,
                              'language':detect_language(text) if language=='auto' else language,'model':group})
        lines = merge_lines(lines)
        return {'text':'\n'.join(line['text'] for line in lines), 'lines':lines,
                'lowConfidence':sum(line['confidence'] < 0.8 for line in lines),
                'reviewCount':sum(len(line.get('review',[])) for line in lines),
                'languageMode':language,'languages':sorted(set(line['language'] for line in lines)),
                'engine':'PP-OCRv5 / CJK server / 10 languages (CPU)',
                'elapsed':round(time.monotonic()-started, 2)}


def tile_starts(length, size=1536, overlap=160):
    starts = list(range(0, max(1, length-size+1), size-overlap))
    last = max(0, length-size)
    if starts[-1] != last:
        starts.append(last)
    return starts


def merge_lines(lines):
    kept = []
    for line in sorted(lines, key=lambda item:item['confidence'], reverse=True):
        a = line['box']
        duplicate = False
        for other in kept:
            b = other['box']
            intersection = max(0,min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
            smaller = min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
            if smaller > 0 and intersection / smaller > 0.65:
                duplicate = True
                break
        if not duplicate:
            kept.append(line)
    kept.sort(key=lambda item:(round(item['box'][1]/10), item['box'][0]))
    return kept
