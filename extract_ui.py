import re
import sys

with open('c:/Coding/Capcraft/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('c:/Coding/Capcraft/extracted_icons.txt', 'w', encoding='utf-8') as out:
    tools = re.findall(r'<button[^>]*class="[^"]*btn-tool[^"]*"[^>]*id="([^"]+)"[^>]*>(.*?)</button>', html, re.DOTALL)
    out.write("--- Tool Buttons ---\n")
    for tid, tcontent in tools:
        icon_match = re.search(r'<span class="icon">(.*?)</span>', tcontent, re.DOTALL)
        icon_text = icon_match.group(1).strip() if icon_match else "None"
        if len(icon_text) > 100:
            icon_text = "SVG..."
        out.write(f"ID: {tid}, Icon: {icon_text}\n")
    
    out.write("\n--- Sub Panel Buttons & Dropdowns ---\n")
    other_btns = re.findall(r'<button[^>]*>(.*?)</button>', html, re.DOTALL)
    for b in other_btns:
        b_stripped = b.strip()
        if '<svg' in b_stripped:
            out.write("Button with SVG: " + re.sub(r'<svg.*?</svg>', '<SVG>', b_stripped, flags=re.DOTALL) + "\n")
