import re

for file_path in ['c:/Coding/Capcraft/index.html', 'c:/Coding/Capcraft/guide.html']:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the color for .lucide-crop
    new_content = re.sub(r'\.lucide-crop\s*\{\s*stroke:\s*#[a-zA-Z0-9]+;\s*\}', '.lucide-crop { stroke: #3b82f6; }', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

print("Crop icon color updated to Blue in both files.")
