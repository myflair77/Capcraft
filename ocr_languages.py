"""Language routing and offline labels. Recognition confidence is not a guarantee."""
import re

LANGUAGES={'auto':'자동 판별 (10개 언어·한자)','ko':'한국어','hanja':'한자','en':'영어','es':'스페인어',
           'de':'독일어','fr':'프랑스어','it':'이탈리아어','ru':'러시아어','zh':'중국어','ja':'일본어','th':'태국어'}
GROUPS={'ko':'rec','hanja':'cjk','en':'latin','es':'latin','de':'latin','fr':'latin','it':'latin','ru':'ru','zh':'cjk','ja':'cjk','th':'th'}

def recognition_groups(language):
    if language=='auto':return ['rec','latin','ru','cjk','th']
    if language=='ko':return ['rec','cjk']
    return [GROUPS[language]]
_detector=None

def detect_language(text):
    if re.search('[가-힣]',text):return 'ko'
    if re.search('[ぁ-ヿ]',text):return 'ja'
    if re.search('[\u0e00-\u0e7f]',text):return 'th'
    if re.search('[Ѐ-ӿ]',text):return 'ru'
    if re.search('[一-鿿]',text):return 'zh'
    if sum(c.isalpha() for c in text)<4:return 'unknown'
    global _detector
    if _detector is None:
        from lingua import Language, LanguageDetectorBuilder
        _detector=LanguageDetectorBuilder.from_languages(Language.ENGLISH,Language.SPANISH,
            Language.GERMAN,Language.FRENCH,Language.ITALIAN).build()
    result=_detector.detect_language_of(text)
    return result.iso_code_639_1.name.lower() if result else 'unknown'

def choose_candidate(candidates):
    def rank(row):
        text,score,group=row
        native={'rec':'[가-힣]','cjk':'[一-鿿ぁ-ヿ]','ru':'[Ѐ-ӿ]','th':'[\u0e00-\u0e7f]','latin':'[A-Za-zÀ-ÿ]'}[group]
        compact=''.join(text.split())
        # A model confidently reading only "English" must not replace an
        # otherwise well-recognized Korean/English sentence containing it.
        partial=any(other_score>=.85 and compact and compact in ''.join(other.split())
                    and len(''.join(other.split()))>=len(compact)*1.5
                    for other,other_score,_ in candidates)
        return score + (0.015 if re.search(native,text) else 0) - (0.2 if not text.strip() else 0) - (.12 if partial else 0)
    return max(candidates,key=rank)
