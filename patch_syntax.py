import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace </script> with <\/script> inside the printWindow template literal
# We know the template literal starts at printWindow.document.write(`
# and ends around line 4850.
# A safe way is to replace `</script>` with `<\/script>` in the block of code for printWindow.

old_print_block = r"printWindow\.document\.write\(`([\s\S]*?)`\);"
def repl(m):
    return "printWindow.document.write(`" + m.group(1).replace("</script>", r"<\/script>") + "`);"

content = re.sub(old_print_block, repl, content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Print window syntax error fixed!")
