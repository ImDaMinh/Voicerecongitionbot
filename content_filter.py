"""
Content filter to detect inappropriate or nonsensical song requests.
Helps prevent abuse and spam of the music bot.
"""

import re

# 🚫 Blacklisted words/phrases (Vietnamese profanity and common abuse)
BLACKLIST_WORDS = [
    # Vietnamese profanity
    "đm", "dm", "đmm", "dmm", "đệch", "dech",
    "vl", "vcl", "vãi", "vai", "lồn", "lon",
    "cặc", "cac", "buồi", "buoi", "chó", "cho",
    "loz", "lol", "cc", "clgt", "clmm",
    "đĩ", "di", "cave", "gái", "gai",
    "mẹ", "me", "bố", "bo", "cha", "má", "ma",
    "fuck", "shit", "bitch", "ass", "damn",
    "dick", "pussy", "cock", "cunt",
    
    # Common nonsense patterns
    "zzz", "xxx", "test", "testing",
    "asdf", "qwer", "1234",
]

# ✅ Whitelist patterns (if song name contains these, it's likely valid)
WHITELIST_PATTERNS = [
    r'\d+',  # Contains numbers (often in song titles)
    r'[a-zA-Z]{3,}',  # Contains English words (3+ chars)
]

# 🎵 Common music-related keywords (helps identify real song requests)
MUSIC_KEYWORDS = [
    "remix", "cover", "acoustic", "live", "official",
    "mv", "music video", "audio", "lyrics",
    "ft", "feat", "featuring",
    "version", "edit", "mix",
]

def contains_blacklisted_word(text):
    """
    Check if text contains any blacklisted words.
    Returns (is_blacklisted, matched_word)
    """
    text_lower = text.lower()
    
    # Split into words for exact matching
    words = re.findall(r'\w+', text_lower)
    
    for word in words:
        if word in BLACKLIST_WORDS:
            return True, word
    
    # Also check for substring matches (for compound words)
    for blacklist_word in BLACKLIST_WORDS:
        if len(blacklist_word) >= 3 and blacklist_word in text_lower:
            return True, blacklist_word
    
    return False, None

def is_likely_valid_song(text):
    """
    Heuristic check if the text is likely a valid song name.
    Returns (is_valid, reason)
    """
    # Check length
    if len(text.strip()) < 2:
        return False, "Tên bài hát quá ngắn"
    
    if len(text) > 100:
        return False, "Tên bài hát quá dài"
    
    # Check if it's just special characters or numbers
    if re.match(r'^[\W\d_]+$', text):
        return False, "Chỉ chứa ký tự đặc biệt"
    
    # Check for excessive repetition (e.g., "aaaaaaa", "hahahaha")
    if re.search(r'(.)\1{5,}', text):
        return False, "Chứa ký tự lặp lại quá nhiều"
    
    # Check for whitelist patterns (likely valid if matches)
    for pattern in WHITELIST_PATTERNS:
        if re.search(pattern, text):
            return True, "OK"
    
    # Check for music keywords
    text_lower = text.lower()
    for keyword in MUSIC_KEYWORDS:
        if keyword in text_lower:
            return True, "OK"
    
    # If it contains at least 2 characters and no obvious red flags, allow it
    if len(text.strip()) >= 2:
        return True, "OK"
    
    return False, "Không rõ ràng"

def filter_song_request(song_query):
    """
    Main filter function. Returns (is_allowed, reason).
    
    Args:
        song_query: The song name/query to check
    
    Returns:
        (bool, str): (is_allowed, reason_message)
    """
    # First check for blacklisted words
    is_blacklisted, matched_word = contains_blacklisted_word(song_query)
    if is_blacklisted:
        return False, f"Phát hiện từ không phù hợp: '{matched_word}'"
    
    # Then check if it's a likely valid song
    is_valid, reason = is_likely_valid_song(song_query)
    if not is_valid:
        return False, f"Yêu cầu không hợp lệ: {reason}"
    
    return True, "OK"

# 🧪 Test cases
if __name__ == "__main__":
    test_cases = [
        "despacito",
        "nắng ấm xa dần",
        "see tình",
        "con mẹ mày",
        "đm",
        "zzzzz",
        "a",
        "shape of you",
        "test 123",
        "!@#$%",
    ]
    
    print("🧪 Testing content filter:\n")
    for query in test_cases:
        is_allowed, reason = filter_song_request(query)
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"{status}: '{query}' - {reason}")
