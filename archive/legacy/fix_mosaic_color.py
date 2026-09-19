import re

for file_path in ['c:/Coding/Capcraft/index.html', 'c:/Coding/Capcraft/guide.html']:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the grouped CSS rule with two separate ones
    new_content = re.sub(
        r'\.lucide-droplets,\s*\.lucide-crop\s*\{\s*stroke:\s*#[a-zA-Z0-9]+;\s*\}',
        '.lucide-droplets { stroke: #10b981; }\n        .lucide-crop { stroke: #3b82f6; }',
        content
    )
    
    # Also just in case they are already separated or my previous regex was weird
    new_content = re.sub(
        r'\.lucide-droplets\s*\{\s*stroke:\s*#3b82f6;\s*\}',
        '.lucide-droplets { stroke: #10b981; }',
        new_content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

print("Mosaic icon color restored to Green, Crop remains Blue in both files.")
