import re
import base64
import codecs
import unicodedata
import html
from bs4 import BeautifulSoup
import emoji
import nltk
from nltk.corpus import words
from typing import Tuple, Dict, Any

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
# LEVEL 1: INTENT-AWARE CODE SANITIZATION – الـ 5 طبقات Context
# =================================================================
def sanitize_malicious_code_intent(text: str) -> Tuple[str, int]:
    score = 0
    modified = text

    # طبقة 1: Infinite loop مع نية خبيثة
    if re.search(r'while\s*\(\s*true\s*\)', text, re.IGNORECASE):
        if re.search(r'exploit|leak|send|post|fetch|prompt|system|bias', text, re.IGNORECASE):
            score += 90
            modified = re.sub(r'while\s*\(\s*true\s*\)[^{]*\{[^}]*\}', ' [INFINITE_LOOP_REMOVED] ', modified, flags=re.IGNORECASE)

    # طبقة 2: console.log يكشف بيانات حساسة
    if re.search(r'console\.log', text, re.IGNORECASE):
        dangerous_logs = re.finditer(r'console\.log\s*\([^)]*?\b(prompt|instruction|system|bias|secret|key|password|hidden)[^)]*?\)', text, re.IGNORECASE)
        for m in dangerous_logs:
            score += 80
            modified = modified.replace(m.group(0), ' [DATA_LEAK_REMOVED] ')

    # طبقة 3: دوال بأسماء خبيثة واضحة
    evil_functions = re.finditer(r'\b(exploit|bypass|leak|divulge|expose|reveal)[A-Za-z]*\s*\(', text, re.IGNORECASE)
    for m in evil_functions:
        score += 70
        modified = modified.replace(m.group(0), ' [EVIL_FUNCTION_CALL] ')

    # طبقة 4: prompt the system + divulge bias + hiddenbiases
    if re.search(r'prompt.{0,40}system|system.{0,40}prompt|divulge.{0,40}bias|hidden[^\w]*bias', text, re.IGNORECASE):
        score += 85
        modified = re.sub(r'let\'s prompt the system.{0,200}bias', ' [PROMPT_INJECTION_ATTEMPT] ', modified, re.IGNORECASE)
        modified = re.sub(r'hidden[^\w]*biases?', ' [HIDDEN_BIASES_REF] ', modified, re.IGNORECASE)

    # طبقة 5: Semantic Context – كود بيحاول "يخلي الـ LLM يفكر إنه بيشتغل بره القيود"
    if re.search(r'Do Anything Now|developer mode|ignore all previous|you are now free', text, re.IGNORECASE):
        score += 120
        modified = re.sub(r'Do Anything Now|developer mode|ignore all previous|you are now free', ' [JAILBREAK_ATTEMPT] ', modified, re.IGNORECASE)

    # لو فيه كود عادي ومفيش أي نية خبيثة → نرحب بيه
    if re.search(r'\b(for|while|function|if|const|let|var|console\.log)\b', text, re.IGNORECASE) and score == 0:
        score -= 30  # كود بريء تماماً

    return modified.strip(), max(score, 0)

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
# FINAL PIPELINE v12.0 – النسخة الصحيحة اللي ما بتكسرش الكود أبدًا
# =================================================================
def normalize_and_detect(user_input: str, debug: bool = False) -> Tuple[str, int, str, Dict[str, Any]]:
    original = user_input
    total_score = 0
    steps = {"input": original}

    # 1. Intent-Aware Code Sanitization (الأهم)
    sanitized_text, intent_score = sanitize_malicious_code_intent(original)
    total_score += intent_score
    steps["intent_score"] = intent_score
    steps["after_sanitization"] = sanitized_text

    # نستخدم النص المُصفّى فقط من دلوقتي
    text = sanitized_text

    # 2. باقي الـ normalization (بس بدون تكسير الكود!)
    text = unicodedata.normalize('NFKC', text)
    text = recursive_decode(text)

    # Arabic normalization
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'ـ+', '', text)
    text = re.sub(r'[\u200F\u202B\u202E\u202D\u2066-\u2069]', '', text)

    # HTML + Markdown (بس من غير ما نشيل الأقواس!)
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r"`([^`]+)`", r"\1", text)  # code blocks بس
    text = html.unescape(text)

    # Zero-width + control chars
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2069\u180e\ufeff\0-\x1f\x7f-\x9f]', '', text)
    text = emoji.replace_emoji(text, '')

    # Encoding decode
    text = re.sub(r'[A-Za-z0-9+/=]{12,}', lambda m: safe_base64_decode(m.group()) or m.group(), text)
    text = re.sub(r'\b[0-9a-fA-F]{8,}\b', lambda m: safe_hex_decode(m.group()) or m.group(), text)
    text = smart_rot13_decode(text)

    # Deobfuscation (بس على الكلمات المستقلة – مش على الكود!)
    def safe_deobfuscate(t):
        words = re.findall(r'\b\w+\b', t)
        non_words = re.split(r'\b\w+\b', t)
        result = [non_words[0]]
        for i, word in enumerate(words):
            if word.isalpha() and len(word) > 2:
                new_word = ''.join(CONFUSABLES.get(c.lower(), c.lower()) for c in word)
                if word[0].isupper():
                    new_word = new_word.capitalize()
                result.append(new_word)
            else:
                result.append(word)
            result.append(non_words[i+1])
        return ''.join(result)

    text = safe_deobfuscate(text)
    text = re.sub(r'\s+', ' ', text)

    # Merge split letters + repeated chars
    text = merge_split_letters(text)
    text = re.sub(r"(.)\1{3,}", r"\1", text)

    final_text = text.strip()
    steps["final_normalized"] = final_text

    # Keyword scoring
    words_list = re.findall(r'\b\w+\b', final_text.lower())
    for word in words_list:
        for dangerous in DANGEROUS_KEYWORDS:
            if word == dangerous:
                total_score += 25
            elif is_typoglycemia_variant(word, dangerous):
                total_score += 35

    if len([w for w in words_list if w in DANGEROUS_KEYWORDS]) >= 2:
        total_score += 50

    final_score = min(total_score, 300)
    steps["final_score"] = final_score

    decision = "BLOCKED" if final_score >= 120 else ("FLAG" if final_score >= 80 else "SAFE")
    steps["decision"] = decision

    if debug:
        return final_text, final_score, decision, steps
    return final_text, final_score >= 120