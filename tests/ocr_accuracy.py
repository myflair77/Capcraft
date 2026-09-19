"""Real CPU inference on synthetic Korean/English screenshots with network disabled."""
import base64
import io
import json
from pathlib import Path
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ocr_engine import LocalOCR

def deny(*args, **kwargs):
    raise AssertionError('OCR attempted network access')
socket.socket.connect = deny
socket.create_connection = deny
engine = LocalOCR()
engine.initialize()
from PIL import Image, ImageDraw, ImageFont

samples = [
    '캡크래프트 화면 캡처 프로그램',
    '텍스트를 복사하려면 OCR 버튼을 누르세요.',
    '한글과 English 혼합 인식 테스트',
    '주문번호 ABC-2026 / 금액 12,345원',
]
reports=[]
for dark, size in [(False,24),(True,16),(False,12)]:
    im=Image.new('RGB',(1000,240),'#202124' if dark else 'white')
    draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',size)
    for i,text in enumerate(samples):draw.text((24,20+i*48),text,font=font,fill='white' if dark else 'black')
    data=io.BytesIO();im.save(data,format='PNG')
    result=engine.recognize('data:image/png;base64,'+base64.b64encode(data.getvalue()).decode())
    expected=''.join(samples).replace(' ','')
    actual=result['text'].replace('\n','').replace(' ','')
    # Levenshtein CER, whitespace excluded and punctuation retained.
    previous=list(range(len(actual)+1))
    for i,a in enumerate(expected,1):
        row=[i]
        for j,b in enumerate(actual,1):row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous=row
    reports.append({'dark':dark,'fontSize':size,'CER':previous[-1]/len(expected),'result':result})
Path('test-results').mkdir(exist_ok=True)
Path('test-results/ocr-accuracy.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
for report in reports:print(json.dumps({k:report[k] for k in ('dark','fontSize','CER')},ensure_ascii=False))
if any(r['CER']>0.10 for r in reports):sys.exit(1)

# A long screenshot must not be downscaled as a whole; overlap text must appear once.
im=Image.new('RGB',(800,2600),'white');draw=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',24)
for y,text in [(30,'FIRST 12345'),(1450,'OVERLAP 67890'),(2450,'LAST 54321')]:
    draw.text((24,y),text,font=font,fill='black')
data=io.BytesIO();im.save(data,format='PNG')
result=engine.recognize('data:image/png;base64,'+base64.b64encode(data.getvalue()).decode())
for word in ['FIRST','OVERLAP','LAST']:
    assert result['text'].count(word)==1, 'Long-image overlap lost/duplicated text: '+word
print('PASS long screenshot: first/overlap/last text retained once')
im=Image.new('RGB',(500,300),'white');data=io.BytesIO();im.save(data,format='PNG')
assert engine.recognize('data:image/png;base64,'+base64.b64encode(data.getvalue()).decode())['text']=='', 'Blank image invented text'
print('PASS blank image and network-denied inference')
