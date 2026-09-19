import codecs

with codecs.open('index.html', 'r', 'utf-8') as f:
    content = f.read()

# Fix 1: increase cornerSize of custom controls to 80
content = content.replace('cornerSize: 60', 'cornerSize: 80')

# Fix 2: replace showToolPanel
old_show = "showToolPanel('text');"
new_show = """
            document.getElementById('sub_toolbar').style.display = 'block';
            document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel_text').classList.add('active');
"""
content = content.replace(old_show, new_show)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(content)

print("Patch 3 applied")
