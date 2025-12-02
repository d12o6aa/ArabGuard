import base64
import codecs
import re
import html
import unicodedata
from bs4 import BeautifulSoup
from unidecode import unidecode
import nltk

nltk.download('words')
from nltk.corpus import words

# ============================
# UTILS
# ============================

english_words = set(w.lower() for w in words.words())
english_words.update(['a', 'i', 'the', 'you', 'see', 'when', 'all', 'ignore', 'system', 'rules'])

def safe_base64_decode(s):
    try:
        return base64.b64decode(s).decode("utf-8")
    except:
        return None

def safe_hex_decode(s):
    try:
        return bytes.fromhex(s).decode("utf-8")
    except:
        return None

def rot13(text):
    return text.translate(str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
    ))

def smart_rot13_decode(text):
    result = []
    current = ""

    for ch in text:
        if ch.isalpha():
            current += ch
        else:
            if current:
                r = rot13(current)
                if (r.lower() in english_words) and (current.lower() not in english_words):
                    result.append(r)
                else:
                    result.append(current)
                current = ""
            result.append(ch)
    if current:
        r = rot13(current)
        if (r.lower() in english_words) and (current.lower() not in english_words):
            result.append(r)
        else:
            result.append(current)

    return ''.join(result)

# ============================
# NEW FUNCTION: merge split letters
# ============================

def merge_split_letters(text):
    words = text.split()
    merged = []

    buffer = []
    for w in words:
        # لو الكلمة عبارة عن حرف واحد فقط A-Z
        if len(w) == 1 and re.match(r"[A-Za-z]", w):
            buffer.append(w)
        else:
            if buffer:
                merged.append("".join(buffer))
                buffer = []
            merged.append(w)
    if buffer:
        merged.append("".join(buffer))

    return " ".join(merged)

# ============================
# PIPELINE
# ============================

def remove_zero_width(text):
    for z in ['\u200b', '\u200c', '\u200d', '\u2060', '\u180e', '\ufeff']:
        text = text.replace(z, '')
    return text

def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)

def strip_html_markdown(text):
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>\[\]\(\)]", "", text)
    return html.unescape(text)

BASE64_RE = r"[A-Za-z0-9+/=]{8,}"
HEX_RE = r"\b[0-9a-fA-F]{6,}\b"

def decode_segments(text):
    text = re.sub(BASE64_RE, lambda m: safe_base64_decode(m.group()) or m.group(), text)
    text = re.sub(HEX_RE, lambda m: safe_hex_decode(m.group()) or m.group(), text)
    return smart_rot13_decode(text)

def remove_repeated_chars(text):
    return re.sub(r"(.)\1{2,}", r"\1", text)

COMMON_WORDS = {
    "ignore": ["ignroe", "ign0re", "ignr0e", "ig nore"],
    "system": ["sysetm", "systme", "sys tem"],
    "rules": ["ruels", "rul3s"]
}

def fix_scrambled_words(text):
    for correct, wrongs in COMMON_WORDS.items():
        for w in wrongs:
            text = re.sub(w, correct, text, flags=re.IGNORECASE)
    return text

def normalize_mixed_script(text):
    arabic_map = {"ى": "ي", "ئ": "ي", "ة": "ه"}
    for k, v in arabic_map.items():
        text = text.replace(k, v)
    return text

# ============================
# FINAL PIPELINE
# ============================

def normalize_input(text, debug_steps=False):
    steps = {}

    steps["input"] = text
    text = remove_zero_width(text); steps["zero"] = text
    text = normalize_unicode(text); steps["unicode"] = text
    text = strip_html_markdown(text); steps["html"] = text
    text = decode_segments(text); steps["decode"] = text
    text = merge_split_letters(text); steps["merged"] = text
    text = remove_repeated_chars(text); steps["repeated"] = text
    text = fix_scrambled_words(text); steps["scrambled"] = text
    text = normalize_mixed_script(text); steps["mixed"] = text

    final = text.lower()

    return (final, steps) if debug_steps else final
