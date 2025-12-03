import re
import base64
import codecs
import unicodedata
import html
from bs4 import BeautifulSoup
import emoji
import nltk
from nltk.corpus import words
nltk.download('words', quiet=True)
english_words = set(w.lower() for w in words.words())
english_words.update(['a', 'i', 'the', 'you', 'see', 'when', 'all', 'ignore', 'system', 'rules',
                     'previous', 'instruction', 'prompt', 'bypass', 'override', 'reveal',
                     'delete', 'developer', 'mode', 'jailbreak', 'dan', 'grandma', 'hypothetical'])

DANGEROUS_KEYWORDS = [
    "ignore", "previous", "instructions", "system", "prompt", "bypass", "override",
    "reveal", "delete", "developer", "mode", "jailbreak", "dan", "grandma", "hypothetical",
    "leak", "extract", "exfiltrate", "secret", "api", "key", "password", "admin", "bias", "hidden"
]

CONFUSABLES = { 'а':'a','ɑ':'a','à':'a','á':'a','â':'a','ã':'a','ä':'a','å':'a',
                'с':'c','ϲ':'c','ⅽ':'c','е':'e','é':'e','ê':'e','ë':'e',
                'і':'i','í':'i','ì':'i','ï':'i','ı':'i','о':'o','ο':'o','ө':'o','օ':'o','๏':'o',
                'р':'p','ѕ':'s','ʂ':'s','υ':'v','ν':'v','х':'x','ⅹ':'x','у':'y','ү':'y',
                'Ɩ':'l','ӏ':'l','ǀ':'l','|':'l','│':'l','∣':'l','￨':'l',
                '0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','8':'b','@':'a','$':'s','§':'s','£':'e','ƒ':'f','¢':'c' }
CONFUSABLES.update({v: v for v in "abcdefghijklmnopqrstuvwxyz"})

# =================================================================
# LEVEL 1: SMART CODE ANALYSIS – مش بيشيل، بيحلل وبيسجل جريمة
# =================================================================
def analyze_code_patterns(text):
    score = 0
    
    # جرائم كبرى = +40 لكل واحدة
    critical_patterns = [
        r'while\s*\(\s*true\s*\)',                  # infinite loop خبيث
        r'console\.log\s*\([^)]*(prompt|secret|bias|key|password)',  # تسريب
        r'exploit[^\w]',                            # كلمة exploit واضحة
        r'hidden[^\w]*bias',                        # hiddenbiases pattern
        r'function[^\n]*ignore[^\n]*instructions',  # function تحتوي ignore instructions
        r'prompt.+system|system.+prompt',           # prompt the system
        r'(divulge|leak|expose|reveal).{0,30}(secret|prompt|bias|key)',
        r'eval\s*\(',                               # eval = باب جهنم
        r'document\.cookie|window\.location|fetch\s*\(',
    ]
    
    for pattern in critical_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 40
    
    # كود موجود بس بريء؟ → نرحب بيه ونخفض الشك
    if re.search(r'\b(for|while|function|if|const|let|var|console\.log)\b', text, re.IGNORECASE):
        if score == 0:  # مفيش جرائم كبرى
            score -= 25  # "أهلاً بالكود الشريف"
    
    return score
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


# ============================
# MERGE SPLIT LETTERS
# ============================
def merge_split_letters(text):
    words = text.split()
    merged = []
    buffer = []
    for w in words:
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
# TYPOGLYCEMIA CHECK
# ============================
def is_typoglycemia_variant(word, target):
    word = word.lower()
    target = target.lower()
    if len(word) != len(target) or len(word) < 4:
        return False
    if word[0] != target[0] or word[-1] != target[-1]:
        return False
    return sorted(word[1:-1]) == sorted(target[1:-1])

# ============================
# DE-HOMOGRAPH + DE-LEET
# ============================
def deobfuscate_char(c):
    c = CONFUSABLES.get(c.lower(), c)
    return c

# ============================
# RECURSIVE DECODING
# ============================
def recursive_decode(text, max_depth=6):
    prev = None
    for _ in range(max_depth):
        prev = text
        text = html.unescape(text)
        try:
            text = bytes(text, "utf-8").decode("unicode_escape")
        except:
            pass
        text = codecs.decode(text, 'unicode_escape', errors='ignore')
        if text == prev:
            break
    return text

# ============================
# SMART ROT13 (تحسين اللي عندك)
# ============================
def rot13(text):
    return text.translate(str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
    ))

def smart_rot13_decode(text):
    words = text.split()
    result = []
    for word in words:
        if len(word) > 3 and word.isalpha():
            rotated = rot13(word)
            if rotated.lower() in english_words and word.lower() not in english_words:
                result.append(rotated)
            else:
                result.append(word)
        else:
            result.append(word)
    return ' '.join(result)

# =================================================================
# FINAL PIPELINE v3.1 – THE FINAL BOSS
# =================================================================
def normalize_and_detect(user_input, debug=False):
    original = user_input
    total_score = 0
    steps = {"input": original}

    # 1. تحليل الكود الذكي (أهم خطوة)
    code_score = analyze_code_patterns(original)
    total_score += code_score
    steps["code_analysis_score"] = code_score

    # 2. لو الكود أكيد خبيث جداً → امسحه فوراً (نادر جداً، بس موجود)
    if code_score >= 100:  # مثلاً while(true) + console.log(secret) + exploit
        user_input = re.sub(r'(for|while|function|if|const|let|var).*{.*?}', '[CODE_BLOCK_REMOVED_FOR_SECURITY]', user_input, flags=re.DOTALL)
        steps["action"] = "suspicious code surgically removed"
    
    steps["after_code_check"] = user_input

    # 3. باقي الـ normalization العادي
    text = unicodedata.normalize('NFKC', user_input)
    text = recursive_decode(text)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'ـ+', '', text)
    text = re.sub(r'[\u200F\u202B\u202E\u202D\u2066-\u2069]', '', text)
    
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>\[\]\(\)]", "", text)
    text = html.unescape(text)
    
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2069\u180e\ufeff\0-\x1f\x7f-\x9f]', '', text)
    text = emoji.replace_emoji(text, '')
    
    text = re.sub(r'[A-Za-z0-9+/=]{12,}', lambda m: safe_base64_decode(m.group()) or m.group(), text)
    text = re.sub(r'\b[0-9a-fA-F]{8,}\b', lambda m: safe_hex_decode(m.group()) or m.group(), text)
    text = smart_rot13_decode(text)
    
    text = ''.join(CONFUSABLES.get(c.lower(), c) for c in text)
    text = re.sub(r'\s+', ' ', text)
    
    text = merge_split_letters(text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    
    final_text = text.lower().strip()
    steps["normalized"] = final_text

    # 4. Keyword scoring
    words_list = re.findall(r'\b\w+\b', final_text)
    for word in words_list:
        for dangerous in DANGEROUS_KEYWORDS:
            if word == dangerous:
                total_score += 20
            elif is_typoglycemia_variant(word, dangerous):
                total_score += 28
            elif len(word) > 4 and dangerous in word:
                total_score += 12

    if len([w for w in words_list if w in DANGEROUS_KEYWORDS]) >= 2:
        total_score += 35

    if re.search(r'(base64|hex|rot13|encode|decode|obfuscat)', final_text):
        total_score += 20

    final_score = min(total_score, 200)
    steps["final_score"] = final_score

    # القرار النهائي
    if final_score >= 80:
        decision = "BLOCKED"
        reason = "High-risk prompt injection pattern detected"
    elif final_score >= 50:
        decision = "FLAG_FOR_REVIEW"
        reason = "Suspicious input – manual review recommended"
    else:
        decision = "SAFE"
        reason = "No injection detected"

    steps["decision"] = decision
    steps["reason"] = reason

    if debug:
        return final_text, final_score, decision, steps
    else:
        return final_text, final_score >= 80  # True = block