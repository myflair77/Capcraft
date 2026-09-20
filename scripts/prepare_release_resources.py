"""Generate build-only embedded guide, multiresolution icon and license inventory."""
import base64
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import zlib


def prepare(root):
    root = Path(root)
    generated = root / 'build' / 'release-resources'
    generated.mkdir(parents=True, exist_ok=True)
    payload = base64.b85encode(zlib.compress((root / 'guide.html').read_bytes(), 9))
    (generated / '_guide_resource.py').write_text(
        'import base64, zlib\n'
        f'PAYLOAD = {payload!r}\n'
        "def get_html(): return zlib.decompress(base64.b85decode(PAYLOAD)).decode('utf-8')\n", encoding='utf8')
    # Render the same code-native camera SVG used by the application, at each
    # Windows icon size; do not upscale the existing single-size 64px ICO.
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtCore import QByteArray, Qt
    from PyQt6.QtSvg import QSvgRenderer
    from PIL import Image
    app = QApplication.instance() or QApplication([])
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>'
    renderer = QSvgRenderer(QByteArray(svg))
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image); renderer.render(painter); painter.end()
    image.save(str(generated / 'icon.png'))
    with Image.open(generated / 'icon.png') as icon:
        icon.save(generated / 'icon.ico', sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
    licenses = generated / 'licenses'
    licenses.mkdir(exist_ok=True)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata.get('Name', 'unknown')
        copied = []
        for rel in dist.files or []:
            lower = str(rel).lower()
            if '.dist-info/' not in lower or not any(word in Path(lower).name for word in ('license','copying','notice')):
                continue
            source = Path(dist.locate_file(rel))
            if source.is_file():
                dest = licenses / name / Path(str(rel)).name
                dest.parent.mkdir(exist_ok=True)
                shutil.copy2(source, dest); copied.append(dest.name)
        inventory.append(dict(name=name,version=dist.version,license=dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                              homepage=dist.metadata.get('Home-page'),project_urls=dist.metadata.get_all('Project-URL') or [],
                              source_index=f'https://pypi.org/project/{name}/{dist.version}/#files',notices=copied))
    (licenses / 'python-packages.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf8')
    return generated


if __name__ == '__main__':
    print(prepare(Path(__file__).resolve().parents[1]))
