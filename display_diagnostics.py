"""Opt-in bounded display diagnostics; never capture the desktop or send data."""
import json
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut


PROBE = r"""
(() => {
    if (window.capcraftDisplayProbe) return true;
    if (typeof canvas === 'undefined') return false;
    const mode = __PROBE_MODE__;
    const rows = [], events = [];
    let down = false;
    const event = e => {
        if (e.type === 'pointerdown') down = true;
        if (e.type === 'pointerup' || e.type === 'pointercancel') down = false;
        events.push({time:Date.now(), type:e.type, x:e.clientX, y:e.clientY});
        if (events.length > 100) events.shift();
    };
    ['pointerdown','pointerup','pointercancel'].forEach(t => document.addEventListener(t,event,true));
    const bounds = el => {
        if (!el) return null;
        const r=el.getBoundingClientRect(), s=getComputedStyle(el);
        return {x:r.x,y:r.y,width:r.width,height:r.height,display:s.display,
            visibility:s.visibility,opacity:s.opacity,clip:s.clipPath,transform:s.transform};
    };
    const sample = () => {
        // Keep identical timers/event recording in the control, without layout
        // reads or canvas readback. Pixels mode must not query DOM geometry.
        if (mode !== 'combined') {
            const row={time:Date.now(),down,mode};
            const el=canvas.lowerCanvasEl;
            if (mode === 'pixels') {
                row.bitmap=[el.width,el.height]; row.pixels=[];
                try {
                    for(const f of [.65,.8,.95]) {
                        const x=Math.floor(el.width/2), y=Math.floor((el.height-1)*f);
                        if(el.width>0 && el.height>0)
                            row.pixels.push({x,y,rgba:Array.from(canvas.contextContainer.getImageData(x,y,1,1).data)});
                    }
                } catch(e) {row.pixelError=String(e);}
            } else if (mode === 'layout') {
                row.canvas=bounds(el);
                row.wrapper=bounds(document.getElementById('canvas_container'));
                row.sidebar=bounds(document.getElementById('sidebar'));
                row.recent=bounds(document.getElementById('recent_list_container'));
                row.hit=document.elementsFromPoint(innerWidth/2,innerHeight*.8).slice(0,6).map(e=>e.id||e.tagName);
            }
            rows.push(row); if(rows.length>300) rows.shift();
            return;
        }
        const el=canvas.lowerCanvasEl, rect=el.getBoundingClientRect();
        const row={time:Date.now(),down,dpr:devicePixelRatio,viewport:[innerWidth,innerHeight],
            bitmap:[el.width,el.height],canvas:bounds(el),
            wrapper:bounds(document.getElementById('canvas_container')),
            sidebar:bounds(document.getElementById('sidebar')),
            recent:bounds(document.getElementById('recent_list_container')),
            objects:canvas.getObjects().length,pixels:[],hit:[]};
        // Sample the currently visible lower canvas, not just offscreen bitmap edges.
        try {
            for (const f of [.65,.8,.95]) {
                const y=Math.min(innerHeight-2,rect.bottom-2)*f;
                const x=Math.max(0,Math.min(innerWidth-2,rect.left+rect.width/2));
                const px=Math.floor((x-rect.left)*el.width/rect.width);
                const py=Math.floor((y-rect.top)*el.height/rect.height);
                row.pixels.push({x,y,px,py,rgba:px>=0&&py>=0&&px<el.width&&py<el.height
                    ?Array.from(canvas.contextContainer.getImageData(px,py,1,1).data):null});
                row.hit.push({x,y,stack:document.elementsFromPoint(x,y).slice(0,6).map(e=>e.id||e.className||e.tagName)});
            }
        } catch(e) { row.pixelError=String(e); }
        rows.push(row); if(rows.length>300) rows.shift();
    };
    sample();
    const timer=setInterval(sample,100);
    window.capcraftDisplayProbe={rows,events,timer,
        dump:()=>({mode,markedAt:Date.now(),rows:rows.slice(),events:events.slice()})};
    return true;
})()
"""


def probe_mode():
    mode = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--display-probe=')), 'combined')
    if mode not in ('combined','pixels','layout','control'):
        raise ValueError('display-probe must be combined, pixels, layout or control')
    return mode


class DisplayDiagnostics(QObject):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.mode = probe_mode()
        self.pending = False
        self.output = Path(__file__).resolve().parent / 'test-results' / 'display-diagnostics'
        view.loadFinished.connect(self.loaded)
        self.shortcut = QShortcut(QKeySequence('F8'), view)
        self.shortcut.activated.connect(self.mark)
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.checkpoint)

    def loaded(self, ok):
        if ok:
            self.view.page().runJavaScript(PROBE.replace('__PROBE_MODE__',json.dumps(self.mode)), self.installed)

    def installed(self, ok):
        if ok:
            self.timer.start()
            self.view.window().setWindowTitle(self.view.window().windowTitle() + ' [display: '+self.mode+']')
            print('DISPLAY DIAGNOSTICS ['+self.mode+']: recording; press F8 when blanking occurs. ' + str(self.output), flush=True)

    def checkpoint(self):
        self.save(False)

    def mark(self):
        self.save(True)

    def save(self, marked):
        if self.pending:
            return
        self.pending = True
        requested_at = datetime.now().isoformat()
        def received(value):
            self.pending = False
            if not value:
                return
            try:
                report=json.loads(value)
                report.update(requestedAt=requested_at, qtDpr=self.view.devicePixelRatioF(),
                              qtSize=[self.view.width(),self.view.height()], marked=marked)
                self.output.mkdir(parents=True,exist_ok=True)
                name=('mark-'+self.mode+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')) if marked else 'latest-'+self.mode
                (self.output/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False),encoding='utf8')
                if marked:
                    print('DISPLAY MARK saved: '+str(self.output/(name+'.json')),flush=True)
            except (OSError,ValueError) as error:
                print('DISPLAY DIAGNOSTICS ERROR: '+str(error),flush=True)
        self.view.page().runJavaScript(
            'window.capcraftDisplayProbe ? JSON.stringify(capcraftDisplayProbe.dump()) : null',received)


def install_display_diagnostics(view):
    return DisplayDiagnostics(view)
