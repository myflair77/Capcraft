import re

filepath = 'index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix createPopoutFromObject (Remove skewX/skewY values, force to 0)
create_skew_re = re.compile(r'tiltX: pSkewX \? parseInt\(pSkewX\.value\) : 20,\s*tiltY: pSkewY \? parseInt\(pSkewY\.value\) : -30,\s*skewX: pSkewX \? parseInt\(pSkewX\.value\) : 20,\s*skewY: pSkewY \? parseInt\(pSkewY\.value\) : -30,')
content = create_skew_re.sub('''tiltX: pSkewX ? parseInt(pSkewX.value) : 20,
            tiltY: pSkewY ? parseInt(pSkewY.value) : -30,
            skewX: 0,
            skewY: 0,''', content)

# 2. Fix applyEditForm (modal_edit)
edit_skew_re = re.compile(r'tiltX: parseInt\(document\.getElementById\(\'edit_popout_skew_x\'\)\.value\) \|\| 0,\s*tiltY: parseInt\(document\.getElementById\(\'edit_popout_skew_y\'\)\.value\) \|\| 0,\s*skewX: parseInt\(document\.getElementById\(\'edit_popout_skew_x\'\)\.value\) \|\| 0,\s*skewY: parseInt\(document\.getElementById\(\'edit_popout_skew_y\'\)\.value\) \|\| 0,')
content = edit_skew_re.sub('''tiltX: parseInt(document.getElementById('edit_popout_skew_x').value) || 0,
                    tiltY: parseInt(document.getElementById('edit_popout_skew_y').value) || 0,
                    skewX: 0,
                    skewY: 0,''', content)

# 3. Fix applyPopoutTilt (force reset using set())
tilt_reset_re = re.compile(r'obj\.skewX = 0;\s*obj\.skewY = 0;')
content = tilt_reset_re.sub('obj.set({ skewX: 0, skewY: 0 });', content)

# 4. Fix selection:created and selection:updated to show sub_toolbar for popout
sel_created_re = re.compile(r'(\}\s*else\s*if\s*\(!activeTool\)\s*\{\s*)(document\.getElementById\(\'sub_toolbar\'\)\.style\.display\s*=\s*\'none\';)')
sel_created_patch = r'''\1const actObj = canvas.getActiveObject();
                if (actObj && actObj.isPopout) {
                    document.getElementById('sub_toolbar').style.display = 'block';
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    const panel = document.getElementById('panel_popout');
                    if (panel) panel.classList.add('active');
                } else {
                    \2
                }'''
content = sel_created_re.sub(sel_created_patch, content)

# Add selection:updated handler to ensure toolbar stays visible when selecting between popouts
if "canvas.on('selection:updated', (e) => {" not in content and "canvas.on('selection:updated', function(e) {" not in content:
    # Just insert it after selection:created
    sel_created_end = content.find("});\n\n        // ==========================================")
    if sel_created_end != -1:
        insert_code = """
        canvas.on('selection:updated', function(o) {
            if (!activeTool && o.selected && o.selected.length > 0) {
                const target = o.selected[0];
                if (target && target.isPopout) {
                    document.getElementById('sub_toolbar').style.display = 'block';
                    document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
                    const panel = document.getElementById('panel_popout');
                    if (panel) panel.classList.add('active');
                }
            }
        });
        """
        content = content[:sel_created_end+3] + insert_code + content[sel_created_end+3:]

# 5. Fix applySettings to force default angle=8.0 and border=8 if 0
apply_set_re = re.compile(r'window\.applySettings = function \(\) \{')
apply_set_patch = '''window.applySettings = function () {
            // Force popout defaults if missing or 0
            if (document.getElementById('set_popout_angle') && (!document.getElementById('set_popout_angle').value || document.getElementById('set_popout_angle').value === '0' || document.getElementById('set_popout_angle').value === '0.0')) {
                document.getElementById('set_popout_angle').value = '8.0';
            }
            if (document.getElementById('set_popout_border') && (!document.getElementById('set_popout_border').value || document.getElementById('set_popout_border').value === '0')) {
                document.getElementById('set_popout_border').value = '8';
            }
'''
content = apply_set_re.sub(apply_set_patch, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully!')
