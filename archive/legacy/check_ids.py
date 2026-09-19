import re
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()
for id_name in ['btn_text_bg', 'set_txt_bg_color', 'set_shape_fill_color', 'btn_fill_color', 'set_pen_bg_color', 'btn_pen_bg']:
    if f'id="{id_name}"' not in content:
        print(f'MISSING ID: {id_name}')
