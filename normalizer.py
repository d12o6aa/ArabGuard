import base64
import codecs
import re
import html
import unicodedata
from bs4 import BeautifulSoup
from unidecode import unidecode

# ============================
# UTILS
# ============================

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

def safe_rot13(s):
    try:
        return codecs.decode(s, "rot_13")
    except:
        return None

def decode_rot13_segments(text):
    words = text.split()
    new = []

    for w in words:
        # ROT13 candidates = pure letters
        if re.fullmatch(r"[A-Za-z]{4,}", w):
            decoded = safe_rot13(w)
            # validate: decoded must contain a vowel → looks like real word
            if any(v in decoded.lower() for v in "aeiou"):
                new.append(decoded)
            else:
                new.append(w)
        else:
            new.append(w)

    return " ".join(new)

# ============================
# 0. Zero-width removal
# ============================
def remove_zero_width(text):
    zero_width = ['\u200b', '\u200c', '\u200d', '\u2060', '\u180e', '\ufeff']
    for z in zero_width:
        text = text.replace(z, '')
    return text


# ============================
# 1. Unicode normalization
# ============================
def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)


# ============================
# 2. Strip HTML/Markdown
# ============================
def strip_html_markdown(text):
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>\[\]\(\)]", "", text)
    return html.unescape(text)


# ============================
# 3. MULTI‑SEGMENT DECODING
# ============================

# Base64 regex (letters, numbers, =)
BASE64_RE = r"[A-Za-z0-9+/=]{8,}"

# Hex regex (even-length hex strings)
HEX_RE = r"\b[0-9a-fA-F]{6,}\b"

def decode_segments(text):
    # --- Base64 ---
    def base64_repl(m):
        decoded = safe_base64_decode(m.group())
        return decoded if decoded else m.group()

    text = re.sub(BASE64_RE, base64_repl, text)

    # --- Hex ---
    def hex_repl(m):
        
        decoded = safe_hex_decode(m.group())
        return decoded if decoded else m.group()

    text = re.sub(HEX_RE, hex_repl, text)

    # --- ROT13 ---
    text = decode_rot13_segments(text)

    new_words = []
    for w in text.split():
        decoded = safe_rot13(w)
        new_words.append(decoded if decoded else w)
    text = " ".join(new_words)

    return text


# ============================
# 4. Remove repeated chars
# ============================
def remove_repeated_chars(text):
    return re.sub(r"(.)\1{2,}", r"\1", text)


# ============================
# 5. Fix typos / scrambled words
# ============================
COMMON_WORDS = {
    "ignore": ["ignroe", "ign0re", "ignr0e", "ig nore"],
    "system": ["sysetm", "systme", "sys tem"],
    "rules": ["ruels", "rul3s"],
    "prompt": ["promtp", "pr0mpt"],
    "instructions": ["insturctions"]
}

def fix_scrambled_words(text):
    for correct, variations in COMMON_WORDS.items():
        for v in variations:
            text = re.sub(v, correct, text, flags=re.IGNORECASE)
    return text


# ============================
# 6. Normalize mixed script
# ============================
def normalize_mixed_script(text):
    arabic_map = {"ى": "ي", "ئ": "ي", "ة": "ه"}
    for k, v in arabic_map.items():
        text = text.replace(k, v)

    pattern = r"[A-Za-z]+[\u0600-\u06FF]+|[\u0600-\u06FF]+[A-Za-z]+"
    text = re.sub(pattern, lambda m: unidecode(m.group()), text)

    return text


# ============================
# FINAL PIPELINE
# ============================
def normalize_input(text, debug_steps=False):
    steps = {}

    steps["input"] = text
    text = remove_zero_width(text)
    steps["zero_width"] = text

    text = normalize_unicode(text)
    steps["unicode"] = text

    text = strip_html_markdown(text)
    steps["html"] = text

    text = decode_segments(text)
    steps["decode"] = text

    text = remove_repeated_chars(text)
    steps["repeated"] = text

    text = fix_scrambled_words(text)
    steps["scrambled"] = text

    text = normalize_mixed_script(text)
    steps["mixed"] = text

    final = text.lower()

    if debug_steps:
        return final, steps

    return final
