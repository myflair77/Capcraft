import io, re
content = io.open('index.html', 'r', encoding='utf-8').read()
js = re.search(r'<script>(.*?)</script>', content, re.DOTALL).group(1)
io.open('test_syntax.js', 'w', encoding='utf-8').write(js)
print('JS extracted')
