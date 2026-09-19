import re

file_path = r"c:\Coding\Capcraft\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix text style button IDs in the inject_add_text logic
content = content.replace("document.getElementById('btn_text_bold')", "(document.getElementById('btn_txt_b') || {classList:{contains:()=>false}})")
content = content.replace("document.getElementById('btn_text_italic')", "(document.getElementById('btn_txt_i') || {classList:{contains:()=>false}})")
content = content.replace("document.getElementById('btn_text_underline')", "(document.getElementById('btn_txt_u') || {classList:{contains:()=>false}})")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Text style button IDs fixed.")
