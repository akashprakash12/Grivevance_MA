# fix_po_files.py
import polib
import re

def fix_po_file(path):
    po = polib.pofile(path)
    changes = 0
    
    for entry in po:
        # Fix newline consistency
        original_msgid = entry.msgid
        original_msgstr = entry.msgstr
        
        # Handle newlines at start
        if original_msgid.startswith('\n') and not original_msgstr.startswith('\n'):
            entry.msgstr = '\n' + original_msgstr
            changes += 1
        elif not original_msgid.startswith('\n') and original_msgstr.startswith('\n'):
            entry.msgstr = original_msgstr.lstrip('\n')
            changes += 1
            
        # Handle newlines at end
        if original_msgid.endswith('\n') and not original_msgstr.endswith('\n'):
            entry.msgstr = entry.msgstr + '\n'
            changes += 1
        elif not original_msgid.endswith('\n') and original_msgstr.endswith('\n'):
            entry.msgstr = entry.msgstr.rstrip('\n')
            changes += 1
        
        # Preserve Python format specifiers more robustly
        if '%(' in original_msgid or '{' in original_msgid:
            # Extract all format specifiers from msgid
            py_formats = re.findall(r'(%\([^)]+\)[a-zA-Z]|{[^}]+})', original_msgid)
            
            # Check each format specifier in msgstr
            for spec in py_formats:
                if spec not in original_msgstr:
                    # Insert missing format specifier in a sensible location
                    if not entry.msgstr.strip():
                        # If translation is empty, just use the format specifier
                        entry.msgstr = spec
                    else:
                        # Otherwise append it
                        entry.msgstr += f" {spec}"
                    changes += 1
    
    if changes > 0:
        po.save()
        print(f"Fixed {changes} issues in {path}")
    else:
        print(f"No issues found in {path}")

# Run for all languages
for lang in ['hi', 'ml', 'ta']:
    fix_po_file(f'locale/{lang}/LC_MESSAGES/django.po')