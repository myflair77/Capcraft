"""Run the same editor scenarios in the real Qt WebEngine with a QWebChannel bridge."""
import os
import sys
import json
from pathlib import Path
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
data = tempfile.TemporaryDirectory(prefix='capcraft-test-')
single_history_number = next((int(arg.split('=', 1)[1]) for arg in sys.argv
                              if arg.startswith('--history-number=')), None)
if single_history_number is not None and '--observe-history' not in sys.argv:
    raise SystemExit('--history-number requires --observe-history')
if '--background-only' in sys.argv and single_history_number is None:
    raise SystemExit('--background-only requires --history-number')
if '--solid-background' in sys.argv and '--background-only' not in sys.argv:
    raise SystemExit('--solid-background requires --background-only')
if '--synthetic-background' in sys.argv:
    if '--background-only' not in sys.argv or '--solid-background' in sys.argv:
        raise SystemExit('--synthetic-background requires --background-only, without --solid-background')
if '--half-background' in sys.argv and '--synthetic-background' not in sys.argv:
    raise SystemExit('--half-background requires --synthetic-background')
if '--background-as-object' in sys.argv and '--half-background' not in sys.argv:
    raise SystemExit('--background-as-object requires --half-background')
if '--observe-history' in sys.argv:
    source_dir = Path(os.environ.get('CAPCRAFT_DATA_DIR', str(Path.home())))
    history_source = source_dir / '.capcraft_history.json'
    if history_source.exists():
        if single_history_number is None:
            shutil.copy2(history_source, Path(data.name) / '.capcraft_history.json')
        else:
            history = json.loads(history_source.read_text(encoding='utf8'))
            if not isinstance(history, list) or not 1 <= single_history_number <= len(history):
                raise SystemExit('Thumbnail number is outside the saved history')
            # Badge numbers count backwards from the newest-first storage list.
            selected = history[len(history) - single_history_number]
            if '--background-only' in sys.argv:
                scene = json.loads(selected['json'])
                removed_count = len(scene.get('objects', []))
                # Retain background and scene size; substitute one plain rectangle
                # to permit the same move/resize interaction without original objects.
                scene['objects'] = [dict(type='rect', version=scene.get('version','5.3.0'),
                    originX='left', originY='top', left=100, top=100, width=160, height=110,
                    fill='#286be6', stroke='#17458f', strokeWidth=3, scaleX=1, scaleY=1,
                    angle=0, opacity=1, visible=True)]
                if '--solid-background' in sys.argv:
                    scene.pop('backgroundImage', None)
                    scene['background'] = '#e4eef8'
                    selected['bgColor'] = '#e4eef8'
                    for key in ('bgSrc', 'bgImgCache'):
                        selected.pop(key, None)
                if '--synthetic-background' in sys.argv:
                    import base64
                    import cv2
                    import numpy as np
                    width, height = int(selected['width']), int(selected['height'])
                    if '--half-background' in sys.argv:
                        width, height = width // 2, height // 2
                    pixels = np.empty((height, width, 3), dtype=np.uint8)
                    pixels[:] = (235, 240, 248)
                    for y in range(0, height, 80):
                        pixels[y:y+40] = (210, 225, 240)
                    for x in range(0, width, 160):
                        cv2.line(pixels, (x, 0), (x, height-1), (120, 155, 190), 2)
                    cv2.putText(pixels, f'SYNTHETIC BACKGROUND {width} x {height}', (60, height-80),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (40, 40, 40), 3)
                    ok, encoded = cv2.imencode('.png', pixels)
                    if not ok: raise RuntimeError('Cannot encode synthetic background')
                    src = 'data:image/png;base64,' + base64.b64encode(encoded).decode('ascii')
                    background = scene.get('backgroundImage')
                    if not isinstance(background, dict):
                        # History may store the background only in bgSrc and
                        # recreate a plain fabric.Image during restoration.
                        if not selected.get('bgSrc'):
                            raise SystemExit('No background image source in saved item')
                        background = dict(type='image', left=0, top=0, originX='left', originY='top',
                                          scaleX=1, scaleY=1, opacity=1, angle=0)
                        scene['backgroundImage'] = background
                    print('Original background dimensions:', background.get('width'), background.get('height'),
                          '; replacement dimensions:', width, height, flush=True)
                    background['src'] = src
                    background['width'], background['height'] = width, height
                    selected['bgSrc'] = src
                    selected.pop('bgImgCache', None)
                selected['json'] = json.dumps(scene, ensure_ascii=False)
                for key in ('jsonLight', 'stateHistory', 'historyIndex'):
                    selected.pop(key, None)
                print('Temporary scene: replaced', removed_count, 'original objects with one test rectangle;',
                      'size',selected.get('width'),selected.get('height'),flush=True)
            (Path(data.name) / '.capcraft_history.json').write_text(
                json.dumps([selected], ensure_ascii=False), encoding='utf8')
            print('Loaded only thumbnail', single_history_number, 'from', len(history), 'into temporary history', flush=True)
    elif single_history_number is not None:
        raise SystemExit('No saved capture history found')
os.environ['CAPCRAFT_DATA_DIR'] = data.name
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from main import Backend, configure_display_scaling, configure_rendering

configure_rendering()
configure_display_scaling()
app = QApplication(sys.argv)
errors = []
class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith('POPOUT_PNG_SOURCE '): print(message, flush=True)
        if message.startswith('HALF_BACKGROUND '): print(message, flush=True)
        if message.startswith('SELECTION_'): print(message, flush=True)
        if message.startswith('SELECTION_') and '--observe-history' in sys.argv:
            (ROOT / 'test-results').mkdir(exist_ok=True)
            with (ROOT / 'test-results/selection-live.log').open('a', encoding='utf8') as trace:
                trace.write(message + '\n')
        if level == self.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            errors.append(message)
            print('JS ERROR:', message, flush=True)

view = QWebEngineView()
profile = QWebEngineProfile(view)  # off the record, never use personal browser state
page = Page(profile, view)
view.setPage(page)
if '--diagnose-display' in sys.argv:
    from display_diagnostics import install_display_diagnostics
    display_diagnostics = install_display_diagnostics(view)
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
channel = QWebChannel(page)
backend = Backend(None, view)
channel.registerObject('pyBackend', backend)
page.setWebChannel(channel)
host = QMainWindow()
host.setCentralWidget(view)
host.resize(1400, 1000)
host.setWindowTitle('Capcraft v1.2 - automated verification')
if '--observe-history' in sys.argv and '--no-selection-trace' in sys.argv:
    host.setWindowTitle('Capcraft — 실제 이력 복사본 비교 (원본 보존)')
if single_history_number is not None:
    host.setWindowTitle(f'Capcraft — 원래 {single_history_number}번 이미지 단독 시험 (원본 보존)')
    if '--background-only' in sys.argv:
        host.setWindowTitle(f'Capcraft — {single_history_number}번 배경 + 시험 사각형 (원본 보존)')
        if '--solid-background' in sys.argv:
            host.setWindowTitle('Capcraft — 동일 크기 단색 배경 + 시험 사각형 (원본 보존)')
        if '--synthetic-background' in sys.argv:
            host.setWindowTitle('Capcraft — 동일 크기 시험 배경 이미지 + 사각형 (원본 보존)')
            if '--half-background' in sys.argv:
                host.setWindowTitle('Capcraft — 절반 해상도 배경·동일 표시 크기 (원본 보존)')
            if '--background-as-object' in sys.argv:
                host.setWindowTitle('Capcraft — 배경을 잠긴 일반 이미지 개체로 표시 (원본 보존)')
if '--software-compositing' in sys.argv:
    host.setWindowTitle('Capcraft v1.2 - compositor verification')
if '--presentation-pulse' in sys.argv:
    host.setWindowTitle('Capcraft v1.2 - bounded presentation verification')
if '--default-image-sampling' in sys.argv:
    host.setWindowTitle('Capcraft — 이미지 기본 보간 비교 (원본 보존)')
if '--popout-png-source' in sys.argv:
    host.setWindowTitle('Capcraft — 팝아웃 PNG 표시 비교 (원본 보존)')
if '--popout-no-shadow' in sys.argv:
    host.setWindowTitle('Capcraft — 팝아웃 그림자 제외 비교 (원본 보존)')
finished = False

def finish(result):
    global finished
    if not result:
        return
    if finished:
        return
    finished = True
    timer.stop()
    results = json.loads(result)
    # Record both scales diagnostically: the original UI sizing intentionally
    # disables Qt scaling, so equality is not an application requirement.
    print('Display scale: Qt=', view.devicePixelRatioF(), 'WebEngine=', web_dpr, flush=True)
    results.append(dict(name='Qt JavaScript errors', ok=not errors, errors=errors))
    (ROOT / 'test-results').mkdir(exist_ok=True)
    (ROOT / 'test-results/qt-editor.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    view.grab().save(str(ROOT / 'test-results/qt-editor.png'))
    for row in results:
        print(('PASS ' if row['ok'] else 'FAIL ') + row['name'] + ': ' + row.get('error', ''), flush=True)
    exit_code = 1 if any(not r['ok'] for r in results) else 0
    if '--diagnose-display' in sys.argv:
        display_diagnostics.mark()
    QTimer.singleShot(300 if '--diagnose-display' in sys.argv else 0, lambda: app.exit(exit_code))

def poll():
    page.runJavaScript('window.qtTestResults || null', finish)

web_dpr = -1

def record_web_dpr(value):
    global web_dpr
    web_dpr = float(value or -1)

def loaded(ok):
    if not ok:
        app.exit(2)
        return
    page.runJavaScript('window.devicePixelRatio', record_web_dpr)
    if os.environ.get('CAPCRAFT_GRAPHICS_PROBE') == '1':
        print('DPI QT', view.devicePixelRatioF(), 'VIEW', view.width(), view.height(), flush=True)
        page.runJavaScript('JSON.stringify({dpr:devicePixelRatio,width:innerWidth,height:innerHeight})',
                           lambda value: print('DPI WEB', value, flush=True))
    if '--presentation-pulse' in sys.argv:
        page.runJavaScript((ROOT / 'presentation-refresh.js').read_text(encoding='utf8') + '\ninstallPresentationRefresh();')
    if '--benchmark-recent' in sys.argv:
        source = (ROOT / 'tests/recent-performance.js').read_text(encoding='utf8')
        page.runJavaScript(source)
        timer.start(500)
        return
    if '--benchmark' in sys.argv:
        source = (ROOT / 'tests/rendering-scene.js').read_text(encoding='utf8')
        source += (ROOT / 'tests/qt-performance.js').read_text(encoding='utf8')
        if '--readback-gesture' in sys.argv:
            source = 'window.benchmarkReadbackGesture=true;\n' + source
        page.runJavaScript(source + '\nrunQtPerformance().then(r => {console.log(JSON.stringify(r)); window.qtTestResults = JSON.stringify(r);});')
        timer.start(500)
        return
    if '--ocr' in sys.argv:
        source = (ROOT / 'tests/qt-ocr.js').read_text(encoding='utf8')
        page.runJavaScript(source)
        timer.start(500)
        return
    if '--observe-history' in sys.argv:
        if '--half-background' in sys.argv:
            # The normal history loader recreates background from bgSrc at scale
            # 1. Adjust once AFTER restoration, without any periodic pixel reads.
            page.runJavaScript('''(() => {
                let attempts=0;
                const ready=setInterval(() => {
                    if (++attempts>200) {clearInterval(ready);console.error('Half-background restore timed out');return;}
                    if (typeof activeRecentIdx==='undefined' || activeRecentIdx!==0 || _recentLoading || !canvas.backgroundImage) return;
                    clearInterval(ready);
                    const bg=canvas.backgroundImage;
                    bg.set({scaleX:canvas.width/bg.width,scaleY:canvas.height/bg.height});
                    if (__AS_OBJECT__) {
                        const previousHistory=isHistoryAction;
                        isHistoryAction=true;
                        try {
                            canvas.backgroundImage=null;
                            bg.set({selectable:false,evented:false,lockMovementX:true,lockMovementY:true,
                                lockScalingX:true,lockScalingY:true,lockRotation:true,
                                isBgImage:true,isTemp:true,objectCaching:false});
                            canvas.insertAt(bg,0);
                        } finally {isHistoryAction=previousHistory;}
                    }
                    canvas.requestRenderAll();
                    console.log('HALF_BACKGROUND '+JSON.stringify({bitmap:[bg.width,bg.height],display:[bg.getScaledWidth(),bg.getScaledHeight()],canvas:[canvas.width,canvas.height],asObject:__AS_OBJECT__,backgroundCleared:canvas.backgroundImage===null}));
                },50);
            })()'''.replace('__AS_OBJECT__', 'true' if '--background-as-object' in sys.argv else 'false'))
        if '--no-selection-trace' not in sys.argv:
            source = (ROOT / 'tests/selection-trace.js').read_text(encoding='utf8')
            page.runJavaScript(source + '\ninstallSelectionTrace();')
        return
    if '--interactive' in sys.argv:
        scenario = 'selection' if '--selection' in sys.argv else ('recent' if '--recent' in sys.argv else 'rendering')
        source = (ROOT / f'tests/{scenario}-scene.js').read_text(encoding='utf8')
        if '--comparison' in sys.argv:
            source += (ROOT / 'tests/comparison-scene.js').read_text(encoding='utf8')
            page.runJavaScript(source + '\nprepareComparisonScene();')
        else:
            page.runJavaScript(source + '\nprepare' + scenario.capitalize() + 'Scene();')
        return
    source = (ROOT / 'tests/editor-scenarios.js').read_text(encoding='utf8')
    page.runJavaScript(source + '\nrunEditorTests().then(r => window.qtTestResults = JSON.stringify(r)).catch(e => window.qtTestResults = JSON.stringify([{name:"suite",ok:false,error:String(e)}]));')
    timer.start(500)

timer = QTimer()
timer.timeout.connect(poll)
page.loadFinished.connect(loaded)
test_url = QUrl.fromLocalFile(str(ROOT / 'index.html'))
diagnostic_query = []
if '--default-image-sampling' in sys.argv: diagnostic_query.append('default-image-sampling=1')
if '--popout-png-source' in sys.argv: diagnostic_query.append('popout-png-source=1')
if '--popout-no-shadow' in sys.argv: diagnostic_query.append('popout-no-shadow=1')
test_url.setQuery('&'.join(diagnostic_query))
page.load(test_url)
if '--interactive' in sys.argv or '--observe-history' in sys.argv:
    host.showMaximized()
else:
    host.show()
QTimer.singleShot(600000 if '--interactive' in sys.argv or '--observe-history' in sys.argv else 120000, lambda: app.exit(3))
code = app.exec()
view.close()
data.cleanup()
sys.exit(code)
