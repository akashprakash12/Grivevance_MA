import polib
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re

# === Configuration ===
FILES = [
    ('locale/hi/LC_MESSAGES/django.po', 'hi'),
    ('locale/ml/LC_MESSAGES/django.po', 'ml'),
    ('locale/ta/LC_MESSAGES/django.po', 'ta'),
]

# === Rate-limiting for Google Translate API ===
MAX_WORKERS = 3
DELAY_BETWEEN_REQUESTS = 0.5  # in seconds

# === Regex for detecting format strings like %(subject)s ===
FORMAT_RE = re.compile(r'%\([a-zA-Z0-9_]+\)[sd]')

def mask_format_strings(text):
    """Replace format placeholders with temp tokens."""
    placeholders = FORMAT_RE.findall(text)
    masked = text
    for i, ph in enumerate(placeholders):
        masked = masked.replace(ph, f"__PLACEHOLDER{i}__")
    return masked, placeholders

def unmask_format_strings(text, placeholders):
    """Restore format placeholders after translation."""
    unmasked = text
    for i, ph in enumerate(placeholders):
        unmasked = unmasked.replace(f"__PLACEHOLDER{i}__", ph)
    return unmasked

def translate_entry(args):
    entry, lang = args
    if entry.msgstr == "" and entry.msgid.strip():
        try:
            masked_msgid, placeholders = mask_format_strings(entry.msgid)
            time.sleep(DELAY_BETWEEN_REQUESTS)
            translated = GoogleTranslator(source='auto', target=lang).translate(masked_msgid)
            entry.msgstr = unmask_format_strings(translated, placeholders)
            return (entry, entry.msgstr)
        except Exception as e:
            print(f"  ✗ {entry.msgid[:60]!r}...: {e}")
            return (entry, None)
    return (entry, None)

def translate_po_file(path, lang):
    po = polib.pofile(path)
    print(f"\n🔁 Translating {path} → {lang}")
    translated_count = 0

    entries_to_translate = [(entry, lang) for entry in po if entry.msgstr == "" and entry.msgid.strip()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(translate_entry, args) for args in entries_to_translate]

        for future in as_completed(futures):
            entry, translation = future.result()
            if translation:
                translated_count += 1

    po.save()
    print(f"  ✅ Translated {translated_count} entries.")
    return translated_count

if __name__ == "__main__":
    total_translated = 0
    for path, lang in FILES:
        total_translated += translate_po_file(path, lang)
    print(f"\n✅ Total translations completed: {total_translated}")
