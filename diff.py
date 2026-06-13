import difflib
import io

with open('c:/Coding/Capcraft/index_backup.html', 'r', encoding='utf-8') as f1, \
     open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8') as f2:
    text1 = f1.readlines()
    text2 = f2.readlines()

d = list(difflib.unified_diff(text1, text2, n=0))
with open('c:/Coding/Capcraft/diff.txt', 'w', encoding='utf-8') as f:
    f.writelines(d)
