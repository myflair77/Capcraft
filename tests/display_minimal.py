"""Independent Qt canvas/sidebar repro. Does not import Capcraft or user data."""
import argparse
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--native-dpi',action='store_true')
parser.add_argument('--smoke',action='store_true')
parser.add_argument('--fabric',action='store_true')
parser.add_argument('--layout',action='store_true',help='Fabric plus transformed/clipped Capcraft-style canvas layout')
parser.add_argument('--bitmap',action='store_true',help='Large canvas with a decoded PNG image, implies layout')
parser.add_argument('--trace-resize',action='store_true',help='Record resize/paint/input events without forcing redraw')
args=parser.parse_args()
if args.bitmap: args.layout=True
if not args.native_dpi:
    os.environ['QT_ENABLE_HIGHDPI_SCALING']='0'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QUrl,QTimer,qVersion,QObject,QEvent
from PyQt6.QtGui import QShortcut,QKeySequence
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

app=QApplication(sys.argv)
view=QWebEngineView()
if args.trace_resize:
    import json
    import time
    from collections import deque
    class ResizeTrace(QObject):
        def __init__(self):
            super().__init__(view)
            self.rows=deque(maxlen=2000)
            self.types={getattr(QEvent.Type,n):n for n in ('Resize','Paint','UpdateRequest',
                'Expose','WindowStateChange','MouseButtonPress','MouseButtonRelease','Show','Hide')}
            self.shortcut=QShortcut(QKeySequence('F8'),view)
            self.shortcut.activated.connect(self.save)
            app.installEventFilter(self)
            app.aboutToQuit.connect(lambda: app.removeEventFilter(self))
        def eventFilter(self,obj,event):
            kind=event.type()
            if kind in self.types and (obj is view.windowHandle() or
                                      isinstance(obj,QWidget) and obj.window() is view):
                row={'timeNs':time.perf_counter_ns(),'event':self.types[kind],
                     'object':obj.metaObject().className()}
                if kind==QEvent.Type.Resize:
                    row['size']=[event.size().width(),event.size().height()]
                self.rows.append(row)
            return False
        def save(self):
            output=Path(__file__).resolve().parents[1]/'test-results'/'resize-diagnostics'
            output.mkdir(parents=True,exist_ok=True)
            target=output/f'mark-{time.time_ns()}.json'
            target.write_text(json.dumps({'qt':qVersion(),'qtDpr':view.devicePixelRatioF(),
                'viewSize':[view.width(),view.height()],'maximized':view.isMaximized(),
                'events':list(self.rows)},ensure_ascii=False),encoding='utf8')
            print('RESIZE MARK:',target,flush=True)
    resize_trace=ResizeTrace()
class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self,level,message,line,source):
        if level==self.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            print(message,flush=True);app.exit(1)
page=Page(view);view.setPage(page)
view.setWindowTitle('Capcraft '+('2560x1600 bitmap isolation' if args.bitmap else 'Fabric + layout' if args.layout else 'Fabric' if args.fabric else 'plain')+' display test — Qt '+qVersion())
if args.trace_resize: view.setWindowTitle(view.windowTitle()+' [F8 resize trace]')
view.resize(1400,900)
def loaded(ok):
    if not ok:app.exit(2);return
    if args.smoke:
        page.runJavaScript("document.getElementById('auto').click()")
        QTimer.singleShot(2500,lambda:page.runJavaScript('JSON.stringify({moves,bitmapReady:window.bitmapReady})',checked))
def checked(value):
    import json
    result=json.loads(value or '{}')
    print('Qt',qVersion(),result,flush=True)
    if args.trace_resize: resize_trace.save()
    app.exit(0 if result.get('moves',0)>10 and (not args.bitmap or result.get('bitmapReady')) else 3)
page.loadFinished.connect(loaded)
url=QUrl.fromLocalFile(str(Path(__file__).with_name('display-fabric.html' if args.fabric or args.layout else 'display-minimal.html').resolve()))
if args.layout:url.setQuery('layout=1'+('&bitmap=1' if args.bitmap else ''))
view.setUrl(url)
if args.bitmap: view.showMaximized()
else: view.show()
QTimer.singleShot(10000 if args.smoke else 600000,lambda:app.exit(4))
sys.exit(app.exec())
