import os
import re

css_addition = """
        /* Lucide Vector Icons Color Coding */
        .lucide-camera { stroke: #3b82f6; } /* Blue - Capture */
        .lucide-type, .lucide-pen-tool, .lucide-shapes { stroke: #8b5cf6; } /* Purple - Editing */
        .lucide-smile, .lucide-image { stroke: #f59e0b; } /* Orange - Insert */
        .lucide-droplets, .lucide-crop { stroke: #10b981; } /* Green - Transform/Adjust */
        .lucide-eraser, .lucide-trash-2, .lucide-x { stroke: #ef4444; } /* Red - Delete/Close */
        .lucide-undo-2, .lucide-redo-2, .lucide-copy, .lucide-folder-open, .lucide-save, .lucide-printer, .lucide-settings, .lucide-info, .lucide-book-open, .lucide-lightbulb, .lucide-keyboard { stroke: #64748b; } /* Slate - System/Utility */

        /* Enhanced Pin Icon */
        .pin-icon { stroke: #fca5a5; opacity: 0.8; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; }
        .pin-icon:hover { stroke: #ef4444; opacity: 1; transform: scale(1.1); }
        .pin-icon.active { stroke: #ef4444; opacity: 1; transform: scale(1.2); filter: drop-shadow(0 0 4px rgba(239, 68, 68, 0.6)); }
"""

# Update index.html
index_file = 'c:/Coding/Capcraft/index.html'
with open(index_file, 'r', encoding='utf-8') as f:
    index_html = f.read()

# First remove old pin-icon css
index_html = re.sub(r'\s*\.pin-icon\s*\{[^}]+\}', '', index_html)
index_html = re.sub(r'\s*\.pin-icon\.active\s*\{[^}]+\}', '', index_html)

if '/* Lucide Vector Icons Color Coding */' not in index_html:
    index_html = index_html.replace('/* Lucide Vector Icons UI CSS */', css_addition + '\n        /* Lucide Vector Icons UI CSS */', 1)

with open(index_file, 'w', encoding='utf-8') as f:
    f.write(index_html)
print("Updated index.html CSS")

# Update guide.html
guide_file = 'c:/Coding/Capcraft/guide.html'
with open(guide_file, 'r', encoding='utf-8') as f:
    guide_html = f.read()

if '/* Lucide Vector Icons Color Coding */' not in guide_html:
    guide_html = guide_html.replace('</style>', f'{css_addition}\n    </style>', 1)

with open(guide_file, 'w', encoding='utf-8') as f:
    f.write(guide_html)
print("Updated guide.html CSS")
