import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ocr_engine import LocalOCR, tile_starts, merge_lines

class OCRTests(unittest.TestCase):
    def test_spatial_alignment_and_local_candidate(self):
        from types import SimpleNamespace
        from ocr_mixed import positioned_chars, choose_local
        info=SimpleNamespace(words=[['A'],['國','字']],word_cols=[[2],[6,8]],line_txt_len=10)
        self.assertEqual(positioned_chars('A 國字',info,100),[('A',20,0),('國',60,2),('字',80,3)])
        self.assertEqual(positioned_chars('mismatch',info,100),[])
        for group,text in [('cjk','國璽'),('ru','Привет'),('th','ภาษา'),('latin','Bonjour')]:
            self.assertEqual(choose_local([(text,.95,group),('()',.99,'rec')],'rec'),(text,.95,group))
        self.assertIsNone(choose_local([('?',.99,'cjk'),('國',.4,'cjk')],'rec'))

    def test_partial_transcript_does_not_win(self):
        from ocr_languages import choose_candidate
        self.assertEqual(choose_candidate([('English',.99,'latin'),('한글과 English 혼용',.94,'rec')])[2],'rec')

    def test_hanja_routing(self):
        from ocr_languages import LANGUAGES, recognition_groups, detect_language
        self.assertIn('hanja',LANGUAGES)
        self.assertEqual(recognition_groups('hanja'),['cjk'])
        for mode in ['ko','auto']:
            self.assertIn('rec',recognition_groups(mode))
            self.assertIn('cjk',recognition_groups(mode))
        self.assertEqual(detect_language('大韓民國'),'zh')
        self.assertEqual(detect_language('대한민국(大韓民國)'),'ko')

    def test_rejects_external_urls_and_paths(self):
        for source in ['https://example.com/capture.png','C:/capture.png','file:///capture.png','data:text/plain;base64,eA==']:
            with self.assertRaises(ValueError):LocalOCR().recognize(source)

    def test_tile_coverage(self):
        for length in [1,1536,1600,3000,8000]:
            starts=tile_starts(length)
            self.assertEqual(starts[0],0)
            self.assertGreaterEqual(starts[-1]+1536,length)
            self.assertTrue(all(b-a<=1376 for a,b in zip(starts,starts[1:])))

    def test_duplicate_overlap_prefers_confidence(self):
        lines=[{'text':'good','box':[0,0,100,20],'confidence':.99},
               {'text':'bad','box':[2,1,99,19],'confidence':.6},
               {'text':'next','box':[0,40,100,60],'confidence':.98}]
        self.assertEqual([row['text'] for row in merge_lines(lines)],['good','next'])

if __name__=='__main__':unittest.main()
