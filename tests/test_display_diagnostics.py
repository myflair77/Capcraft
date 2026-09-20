"""Ensure the A/B probes do not accidentally perform each other's reads."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from display_diagnostics import PROBE


class ProbeIsolationTests(unittest.TestCase):
    def test_isolated_modes_and_bounded_buffer(self):
        for mode in ('pixels', 'layout', 'control', 'combined'):
            with self.subTest(mode=mode):
                setup = r"""
let layoutReads=0, pixelReads=0, tick;
global.window=global;
global.innerWidth=1000;global.innerHeight=800;global.devicePixelRatio=1.75;
const el={width:1000,height:700,id:'canvas',getBoundingClientRect(){layoutReads++;return {x:0,y:0,left:0,top:0,bottom:700,width:1000,height:700};}};
global.document={addEventListener(){},getElementById(){return el;},elementsFromPoint(){layoutReads++;return [el];}};
global.getComputedStyle=()=>{layoutReads++;return {};};
global.setInterval=f=>{tick=f;return 1;};
global.canvas={lowerCanvasEl:el,getObjects:()=>[],contextContainer:{getImageData(){pixelReads++;return {data:[1,2,3,255]};}}};
"""
                check = """
for(let i=0;i<310;i++)tick();
const data=capcraftDisplayProbe.dump();
if(data.rows.length!==300)throw Error('unbounded buffer');
if(data.rows.some(r=>r.pixelError))throw Error('pixel sampling failed');
console.log(JSON.stringify({layoutReads,pixelReads,mode:data.mode}));
"""
                result=subprocess.run(['node','-e',setup+PROBE.replace('__PROBE_MODE__',json.dumps(mode))+check],capture_output=True,text=True,check=True)
                counts=json.loads(result.stdout)
                self.assertEqual(counts['mode'],mode)
                self.assertEqual(counts['pixelReads']>0,mode in ('pixels','combined'))
                self.assertEqual(counts['layoutReads']>0,mode in ('layout','combined'))


if __name__ == '__main__':
    unittest.main()
