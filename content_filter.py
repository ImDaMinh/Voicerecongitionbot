"""
Content filter to detect inappropriate or nonsensical song requests.
Helps prevent abuse and spam of the music bot.
Smart filtering - only blocks truly inappropriate content, not common words in song titles.
"""

import re

# 🚫 STRICT BLACKLIST - These are ALWAYS blocked (standalone or in phrases)
# Only truly offensive words that would never appear in legitimate song titles
STRICT_BLACKLIST = [
    # Vietnamese profanity (unambiguous)
    "đm", "dm", "đmm", "dmm", "đệch", "dech",
    "vl", "vcl", "lồn", "lon", 
    "cặc", "cac", "buồi", "buoi",
    "loz", "clgt", "clmm",
    "địt", "dit",
    
    # English profanity (explicit)
    "fuck", "fucking", "fucked",
    "dick", "pussy", "cock", "cunt",
    
    # Common nonsense/spam patterns
    "zzzzz", "xxxxx", "asdfgh", "qwerty",
]

# 🔶 CONTEXT-SENSITIVE WORDS - Only blocked when used ALONE or in offensive context
# These words are common in song titles so we need context
CONTEXT_WORDS = {
    # word: [offensive phrases containing this word]
    "mẹ": ["con mẹ", "đụ mẹ", "má mẹ", "mẹ mày", "mẹ nó"],
    "me": [],  # "me" in English is fine, don't block
    "cho": [],  # "cho em", "cho anh" are fine song lyrics
    "chó": ["con chó", "đồ chó"],
    "bố": ["bố mày", "đụ bố"],
    "bo": [],  # Could be a name
    "má": ["đụ má"],
    "ma": [],  # Common word
    "gái": ["con gái điếm", "gái cave"],
    "shit": ["holy shit"],  # Still block most uses
    "bitch": ["son of a bitch"],
    "ass": ["dumb ass", "stupid ass"],  # "bass" should be ok
    "damn": [],  # Common in songs
    "vãi": ["vãi lồn", "vãi cả"],
    "vai": [],  # Common word (shoulder)
    "cc": [],  # Too short, could be initials
    "lol": [],  # Internet slang, not offensive
    "đĩ": ["con đĩ", "đồ đĩ"],
    "di": [],  # Common word
    "cave": ["gái cave"],  # "cave" alone is ok
}

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
    "karaoke", "instrumental",
]

# 🎤 Known safe song titles/artists that might trigger false positives
SAFE_OVERRIDES = [
    "me", "let me", "give me", "show me", "tell me", "take me", "hold me", "love me",
    "cho em", "cho anh", "cho tôi", "cho mình",
    "mama", "papa", "babe", "baby",
    "dance", "bass", "class", "pass", "glass", "mass",
    "assassin", "badass", "jackass",  # Song titles
    "damn daniel", "damn girl",
    "ma baby", "ma love",
    "call me", "kiss me", "miss me", "hit me",
]


def is_in_safe_context(text_lower, word):
    """Check if the word appears in a safe context (like song lyrics)."""
    # Check safe overrides
    for safe_phrase in SAFE_OVERRIDES:
        if safe_phrase in text_lower:
            return True
    
    # If the text is long enough and contains multiple words, it's likely a song title
    words = text_lower.split()
    if len(words) >= 3:
        return True
    
    return False


def contains_blacklisted_content(text):
    """
    Smart check for blacklisted content.
    Returns (is_blacklisted, matched_word)
    """
    text_lower = text.lower().strip()
    words = re.findall(r'\w+', text_lower)
    
    # 1. Check strict blacklist first - always blocked
    for word in words:
        if word in STRICT_BLACKLIST:
            return True, word
    
    # Also check for strict blacklist as substring (for compound words)
    for blacklist_word in STRICT_BLACKLIST:
        if len(blacklist_word) >= 4 and blacklist_word in text_lower:
            return True, blacklist_word
    
    # 2. Check context-sensitive words
    for word in words:
        if word in CONTEXT_WORDS:
            # If word is in safe context, skip it
            if is_in_safe_context(text_lower, word):
                continue
            
            # Check if it appears in an offensive phrase
            offensive_phrases = CONTEXT_WORDS[word]
            for phrase in offensive_phrases:
                if phrase in text_lower:
                    return True, phrase
            
            # If the word stands ALONE (single word query), block it
            if len(words) == 1 and word in ["mẹ", "chó", "bố", "đĩ"]:
                return True, word
    
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
    # First check for blacklisted content (smart check)
    is_blacklisted, matched_word = contains_blacklisted_content(song_query)
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
        "love me like you do",
        "cho em một lần",
        "me and my broken heart",
        "shape of you",
        "con mẹ mày",
        "đm",
        "zzzzz",
        "a",
        "test 123",
        "!@#$%",
        "call me maybe",
        "mama",
        "bass boosted",
    ]
    
    print("🧪 Testing content filter:\n")
    for query in test_cases:
        is_allowed, reason = filter_song_request(query)
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"{status}: '{query}' - {reason}")
