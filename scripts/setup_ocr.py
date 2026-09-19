"""Explicit installation-only model downloader. Never imported by the application."""
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1] / 'models' / 'ocr'
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
for model in manifest['models'].values():
    target = root / model['file']
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == model['sha256']:
        print('Verified:', target.name, flush=True)
        continue
    url = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/' + model['path'] + '/' + model['file']
    temporary = target.with_suffix('.download')
    print('Downloading:', target.name, flush=True)
    try:
        with urllib.request.urlopen(url, timeout=90) as response, temporary.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != model['sha256']:
            raise RuntimeError('Model checksum mismatch: ' + target.name)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print('Verified:', target.name, flush=True)
