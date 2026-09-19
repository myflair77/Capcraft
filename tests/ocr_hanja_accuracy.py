"""Offline integration check for Hanja-only and mixed Korean/Hanja captures."""
import base64
import io
import socket
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ocr_engine import LocalOCR

def deny(*args,**kwargs):
    raise AssertionError('Network access attempted')
socket.socket.connect=deny
socket.create_connection=deny
engine=LocalOCR()
engine.initialize()
from PIL import Image,ImageDraw,ImageFont
samples=['大韓民國 漢字 學校 文化','대한민국(大韓民國)의 교육(敎育)과 문화(文化)']
mixed_suite=len(sys.argv)>1 and sys.argv[1]=='--mixed'
if mixed_suite:
    samples=['한국어 English 혼용 문장','한국어 Привет 러시아어 문장','English 日本語 テスト',
             'Bonjour français und Deutsch','대한민국(大韓民國)의 문화(文化)']
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',32)
image=Image.new('RGB',(1100,max(150,60*len(samples)+20)),'white')
draw=ImageDraw.Draw(image)
for i,text in enumerate(samples):draw.text((20,15+i*60),text,font=font,fill='black')
data=io.BytesIO()
image.save(data,format='PNG')
url='data:image/png;base64,'+base64.b64encode(Path(sys.argv[1]).read_bytes() if len(sys.argv)>1 and not mixed_suite else data.getvalue()).decode()
for mode in (['auto'] if len(sys.argv)>1 else ['hanja','ko','auto']):
    result=engine.recognize(url,mode)
    print(mode,ascii(result['text']),flush=True)
    if mixed_suite:
        from difflib import SequenceMatcher
        expected=''.join(samples).replace(' ','')
        actual=result['text'].replace(' ','').replace('\n','')
        print('MATCH_RATIO',SequenceMatcher(None,expected,actual).ratio(),'SECONDS',result['elapsed'],flush=True)
        assert expected==actual,'Mixed-script fixture changed or lost characters'
        continue
    for token in (['國璽','制誥'] if len(sys.argv)>1 else ['大韓民國','漢字','學校','文化']):
        assert token in result['text'],(mode,token,result['text'])
    if len(sys.argv)==1 and mode in ('ko','auto'):
        assert '대한민국(大韓民國)의' in result['text'],result['text']
