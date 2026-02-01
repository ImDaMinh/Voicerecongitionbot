"""
English Song Recognition Corrector
Cải thiện khả năng nhận dạng tên bài hát tiếng Anh khi người dùng phát âm không chuẩn.

Features:
1. Fuzzy matching với các tên bài hát phổ biến
2. Phonetic correction (sửa lỗi phát âm)
3. Common typo/pronunciation mistakes
4. Levenshtein distance matching
"""

import difflib
import re
from typing import Optional, List, Tuple

# ============================================
# COMMON PRONUNCIATION MISTAKES MAPPING
# Key: What Google might hear -> Value: What user meant
# ============================================
PRONUNCIATION_FIXES = {
    # Common English words mispronunciations
    "di": "the",
    "da": "the",
    "de": "the",
    "dơ": "the",
    "đơ": "the",
    "đu": "do",
    "đi": "the",
    "ai": "i",
    "giu": "you",
    "du": "you",
    "iu": "you",
    "diu": "you",
    "mai": "my",
    "mi": "me",
    "wi": "we",
    "uy": "we",
    "oan": "one",
    "oăn": "one",
    "tu": "to",
    "tô": "to",
    "lo": "love",
    "lô": "love",
    "lạp": "love",
    "lav": "love",
    "lớp": "love",
    "gui": "guy",
    "gai": "guy",
    "gơ": "girl",
    "gơl": "girl",
    "guôn": "girl",
    "bây": "by",
    "bai": "by",
    "bơi": "boy",
    "boi": "boy",
    "hát": "heart",
    "hat": "heart",
    "ha": "heart",
    "wơ": "world",
    "uor": "world",
    "worl": "world",
    "béc": "baby",
    "bay": "baby",
    "bây bi": "baby",
    "bi": "be",
    "bi cause": "because",
    "ưn": "and",
    "en": "and",
    "ơn": "on",
    "sô": "so",
    "so": "soul",
    "nô": "know",
    "no": "know",
    "trai": "try",
    "tru": "true",
    "tru lơ": "true love",
    "can": "con",
    "wái": "why",
    "wai": "why",
    "uai": "why",
    "uhat": "what",
    "oat": "what",
    "húc": "who",
    "hu": "who",
    "hun": "when",
    "uen": "when",
    "wue": "when",
    "der": "there",
    "de re": "there",
    "hier": "here",
    "hi e": "here",
    "ol": "all",
    "phà": "for",
    "pho": "for",
    "pho ever": "forever",
    "pho e ver": "forever",
    "môn": "moon",
    "mun": "moon",
    "san": "sun",
    "xan": "sun",
    "sơn": "sun",
    "stá": "star",
    "xta": "star",
    "sta": "star",
    "nai": "night",
    "nait": "night",
    "dai": "die",
    "lai": "lie",
    "lai pho": "life",
    "life": "life",
    "dơ rim": "dream",
    "drím": "dream",
    "drim": "dream",
    "drem": "dream",
    "nao": "now",
    "nau": "now",
    "lai pho": "life",
    "lit": "light",
    "lài": "light",
    
    # More phonetic mappings for common words
    "ít": "it",
    "ít ít": "is it",
    "ơ": "a",
    "đét": "that",
    "díts": "this",
    "uít": "with",
    "iu ơ": "your",
    "dơ": "your",
    "hơ": "her",
    "him": "him",
    "hít": "his",
    "ải": "i",
    "uơ": "would",
    "cút": "could",
    "sút": "should",
    "uôn": "want",
    "níd": "need",
    "nít": "need",
    "sẹc": "sex",
    "séc": "sec",
    "gét": "get",
    "gọt": "got",
    "cam": "come",
    "gô": "go",
    "tếch": "take",
    "mếch": "make",
    "séc": "shake",
    "sếch": "shake",
    "brếch": "break",
    "brếch mai hát": "break my heart",
    "sai": "sky",
    "cờ lai": "cry",
    "cờ rai": "cry",
    "phai": "fly",
    "phlai": "fly",
    "hái": "high",
    "lâu": "low",
    "xâu": "show",
    "nâu": "know",
    "xâu mi": "show me",
    "teo": "tell",
    "xeo": "sell",
    "bay": "bay",
    "uây": "way",
    "đề": "day",
    "nài": "night",
    "uơ": "were",
    "uoz": "was",
    "đít": "did",
    "giớt": "just",
    "gio": "just",
    "oăn li": "only",
    "ôn li": "only",
    "ơ oen": "again",
    "ờ ghen": "again",
    "pheo": "feel",
    "rin": "real",
    "ri ơ": "real",
    "đao": "though",
    "rao": "road",
    "bơ ri": "bring",
    "lít": "little",
    "bít": "bit",
    "bíc": "big",
    "sô mô": "so much",
    
    # Extended phonetic patterns
    "lai": "like",
    "lai diu đu": "like you do",
    "diu đu": "you do",
    "xép": "shape",
    "ộp": "of",
    "xép ộp": "shape of",
    "xép ộp diu": "shape of you",
    "lớp mi": "love me",
    "lớp mi lai": "love me like",
    "lớp mi lai diu đu": "love me like you do",
    "đét xít": "despacito",
    "đét pa xi tô": "despacito",
    "đét xì tô": "despacito",
    "đét xì pa xi tô": "despacito",
    "báy đinh lai": "blinding lights",
    "bai lâu đinh": "blinding",
    "bai lâu đinh lài": "blinding lights",
    "đen mon ki": "dance monkey",
    "đăng mơn ki": "dance monkey",
    "đăng ki mơn": "dance monkey",
    "xen ni tô": "senorita",
    "xen lái tô": "senorita",
    "xen ri ta": "senorita",
    "ha va na": "havana",
    "ha bà na": "havana",
    "pơ phét": "perfect",
    "pơ phéc": "perfect",
    "sằm oan": "someone",
    "sâm oan lai diu": "someone like you",
    "hê lô": "hello",
    "heo lô": "hello",
    "shi ting ao lao": "thinking out loud",
    "sây ting ao lao": "thinking out loud",
    "bét gai": "bad guy",
    "béc gai": "bad guy",
    "lao li": "lovely",
    "lav li": "lovely",
    "lớp li": "lovely",
    "ô san ai": "ocean eyes",
    "ô sần ai": "ocean eyes",
    "sì tai": "stay",
    "stây": "stay",
    "xì tây": "stay",
    "lê vi tây ting": "levitating",
    "lê vi tê ting": "levitating",
    "đon sờ ta nao": "dont start now",
    "đon sờ tát nao": "dont start now",
    "niu ru": "new rules",
    "niu run": "new rules",
    "đai na mai": "dynamite",
    "đai nờ mai": "dynamite",
    "bơ tơ": "butter",
    "bát tơ": "butter",
    "bát ter": "butter",
    "áp tau phan": "uptown funk",
    "áp tau phăng": "uptown funk",
    "trét sờ": "treasure",
    "trê dờ": "treasure",
    "tua ti pho mê gíc": "24k magic",
    "tua ti pho mé gíc": "24k magic",
    "rô linh in đơ đíp": "rolling in the deep",
    "rô ling in đơ díp": "rolling in the deep",
    "í di ôn mi": "easy on me",
    "íu di ôn mi": "easy on me",
    "lơ iu xeo": "love yourself",
    "lớp iu xeo": "love yourself",
    "so ri": "sorry",
    "xo ri": "sorry",
    "xo ơ ri": "sorry",
    "pít chét": "peaches",
    "pít chít": "peaches",
    "gốt": "ghost",
    "gốt xờ": "ghost",
    "ơ ten sơn": "attention",
    "ê ten sần": "attention",
    "ui đon tóc ê ni mo": "we dont talk anymore",
    "ui đôn tóc ê ni mo": "we dont talk anymore",
    "oan cờ ơ uê": "one call away",
    "oăn cờ ơ uây": "one call away",
    "xì ga": "sugar",
    "xu gà": "sugar",
    "gơ lai diu": "girls like you",
    "gơn lai diu": "girls like you",
    "meo mo ri": "memories",
    "mê mo ri": "memories",
    "meo mô ri": "memories",
    "mu lai gé gờ": "moves like jagger",
    "mu lai jé gờ": "moves like jagger",
    "ro": "roar",
    "ro ờ": "roar",
    "phai ơ uơ": "firework",
    "phai ơ uốc": "firework",
    "đác hót": "dark horse",
    "đác ho": "dark horse",
    "tin ết drim": "teenage dream",
    "tin ê drim": "teenage dream",
    "cờ li pho ni a gơ": "california gurls",
    "cờ li pho ni a gơn": "california girls",
    "sếch ít óp": "shake it off",
    "sếch ít ọp": "shake it off",
    "bơ len xơ pếch": "blank space",
    "blanh xờ pếch": "blank space",
    "lớp xì to ri": "love story",
    "lơ xờ to ri": "love story",
    "en ti hê rô": "anti hero",
    "ăn ti hê rô": "anti hero",
    "ăm bờ re la": "umbrella",
    "ăm bơ re la": "umbrella",
    "đai a mần": "diamonds",
    "đai mần": "diamonds",
    "guốc": "work",
    "uốc": "work",
    "ui phao lơ": "we found love",
    "ui phaon lơ": "we found love",
    "chíp phì reo": "cheap thrills",
    "chíp xì reo": "cheap thrills",
    "sen đơ lia": "chandelier",
    "chan đờ lia": "chandelier",
    "tai ta ni um": "titanium",
    "ti ta ni um": "titanium",
    "ti tà ni um": "titanium",
    "cầu ting xì ta": "counting stars",
    "cao ting xì ta": "counting stars",
    "a pô lo jai": "apologize",
    "ê pô lờ jai": "apologize",
    "sìi cờ rét": "secrets",
    "si cờ rét": "secrets",
    "rây đi ô éc típ": "radioactive",
    "bì li vơ": "believer",
    "bi li vờ": "believer",
    "săn đờ": "thunder",
    "thăn đờ": "thunder",
    "vi và la vi đa": "viva la vida",
    "vi vờ la vi đà": "viva la vida",
    "pa ra đai": "paradise",
    "pa rờ đai": "paradise",
    "đờ xai ơn tít": "the scientist",
    "đờ xai en tít": "the scientist",
    "phích xờ diu": "fix you",
    "phíc diu": "fix you",
    "gie lâu": "yellow",
    "ye lâu": "yellow",
    "eo lâu": "yellow",
    
    # Artist names
    "ai đồ": "adele",
    "a đen": "adele",
    "a sen": "ariana",
    "a ri a na": "ariana",
    "tây lơ": "taylor",
    "tay le suýt": "taylor swift",
    "tay lor swift": "taylor swift", 
    "te ler suipt": "taylor swift",
    "brúi nô": "bruno",
    "bru no": "bruno",
    "bờ ru nô": "bruno mars",
    "bờ ru nô ma": "bruno mars",
    "eđ": "ed",
    "e đ": "ed",
    "e sơ ran": "ed sheeran",
    "é si rơn": "ed sheeran",
    "si a": "sia",
    "xia": "sia",
    "ri hâu": "rihanna",
    "ri ha na": "rihanna",
    "bi yon sê": "beyonce",
    "bi dô li": "billie",
    "bi li i lít": "billie eilish",
    "bi li ai lít": "billie eilish",
    "chanh wơ cơ": "charlie puth",
    "cha li pu": "charlie puth",
    "ját sơn": "justin",
    "gát tinh": "justin",
    "justion biber": "justin bieber",
    "jats tin bi bur": "justin bieber",
    "gát tin bi bơ": "justin bieber",
    "cô vai": "coldplay",
    "côn plây": "coldplay",
    "côn plề": "coldplay",
    "ma ru 5": "maroon 5",
    "ma run phái": "maroon 5",
    "mà run phai": "maroon 5",
    "oăn di rec sơn": "one direction",
    "bít tờ": "bt",
    "bi ti es": "bts",
    "blơ pịt": "blackpink",
    "bơ lắc pin": "blackpink",
    
    # Common song words
    "sề": "say",
    "xề": "say",
    "đồn": "don't",
    "dồn": "dont",
    "đôn": "don't",
    "uôn": "want",
    "uốn": "want",
    "laik": "like",
    "laích": "like",
    "lịt mi": "let me",
    "léc mi": "let me",
    "tích mi": "take me",
    "tek mi": "take me",
    "seng": "sing",
    "xing": "sing",
    "đến": "dance",
    "đen": "dance",
    "đăng": "dance",
    "pheo": "feel",
    "phiu": "feel",
    "fiu": "feel",
    "gút": "good",
    "guốt": "good",
    "xo": "show",
    "sô": "show",
    "mi sô": "me so",
    "sơ mơ": "summer",
    "sặc mơ": "summer",
    "săm mờ": "summer",
    "uình": "win",
    "uin": "win",
    "lút": "lose",
    "lu": "lose",
    
    # Numbers in songs
    "oăn": "one",
    "tu": "two",
    "tư": "two",
    "tờ ri": "three",
    "xờ ri": "three",
    "pho": "four",
    "phai": "five",
    "xích": "six",
    "xe ven": "seven",
    "ét": "eight",
    "nai": "nine",
    "ten": "ten",
}

# ============================================
# POPULAR ENGLISH SONG TITLES
# For fuzzy matching
# ============================================
POPULAR_SONGS = [
    # Pop hits
    "shape of you", "blinding lights", "dance monkey", "someone like you",
    "hello", "perfect", "thinking out loud", "photograph", "castle on the hill",
    "bad guy", "lovely", "ocean eyes", "everything i wanted", "happier",
    "drivers license", "good 4 u", "traitor", "deja vu", "brutal",
    "watermelon sugar", "as it was", "late night talking", "matilda",
    "stay", "industry baby", "montero", "thats what i want",
    "levitating", "dont start now", "new rules", "one kiss",
    "dynamite", "butter", "permission to dance", "boy with luv",
    "kill this love", "how you like that", "ice cream", "pink venom",
    "despacito", "havana", "senorita", "in my feelings",
    "uptown funk", "treasure", "24k magic", "thats what i like",
    "rolling in the deep", "set fire to the rain", "skyfall", "easy on me",
    "love yourself", "sorry", "peaches", "ghost", "baby",
    "attention", "we dont talk anymore", "one call away", "marvin gaye",
    "closer", "something just like this", "dont let me down", "roses",
    "sugar", "girls like you", "memories", "moves like jagger",
    "roar", "firework", "dark horse", "teenage dream", "california gurls",
    "shake it off", "blank space", "love story", "anti hero",
    "umbrella", "diamonds", "work", "we found love",
    "cheap thrills", "chandelier", "titanium", "elastic heart",
    "counting stars", "apologize", "secrets", "its time",
    "radioactive", "believer", "thunder", "whatever it takes",
    "viva la vida", "paradise", "the scientist", "fix you", "yellow",
    
    # Classic hits
    "bohemian rhapsody", "we are the champions", "dont stop me now",
    "sweet child o mine", "november rain", "welcome to the jungle",
    "hotel california", "stairway to heaven", "imagine",
    "billie jean", "thriller", "beat it", "smooth criminal",
    "i will always love you", "my heart will go on", "hero",
    "let it go", "into the unknown", "how far ill go",
    "cant help falling in love", "unchained melody", "careless whisper",
    
    # Current popular
    "anti hero", "midnight rain", "karma", "lavender haze",
    "flowers", "unholy", "hold me closer", "sunroof",
    "as it was", "running up that hill", "about damn time",
    "heat waves", "enemy", "unstoppable", "i aint worried",
]

# ============================================
# COMMON TYPO PATTERNS
# ============================================
TYPO_CORRECTIONS = {
    # Double letters often missed
    "beutiful": "beautiful",
    "beatiful": "beautiful",
    "belive": "believe",
    "believ": "believe",
    "diferent": "different",
    "realy": "really",
    "actualy": "actually",
    "finaly": "finally",
    "basicly": "basically",
    "definetly": "definitely",
    "tomorow": "tomorrow",
    "tommorow": "tomorrow",
    "untill": "until",
    "occured": "occurred",
    "hapend": "happened",
    "hapened": "happened",
    
    # Silent letters
    "nife": "knife",
    "nock": "knock",
    "nom": "know",
    "rong": "wrong",
    "rite": "right",
    "lisen": "listen",
    "casle": "castle",
    
    # Vowel confusion
    "thier": "their",
    "recieve": "receive",
    "wierd": "weird",
    "freind": "friend",
    
    # Common song title typos
    "somone": "someone",
    "somthing": "something",
    "everithing": "everything",
    "evrything": "everything",
    "togeter": "together",
    "beatiful": "beautiful",
    "dangerious": "dangerous",
    "begining": "beginning",
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase
    text = text.lower().strip()
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def apply_pronunciation_fixes(text: str) -> str:
    """Apply Vietnamese to English pronunciation fixes."""
    words = text.lower().split()
    fixed_words = []
    
    i = 0
    while i < len(words):
        # Try to match 3-word phrases first, then 2-word, then single word
        matched = False
        
        for phrase_len in [3, 2]:
            if i + phrase_len <= len(words):
                phrase = ' '.join(words[i:i+phrase_len])
                if phrase in PRONUNCIATION_FIXES:
                    fixed_words.append(PRONUNCIATION_FIXES[phrase])
                    i += phrase_len
                    matched = True
                    break
        
        if not matched:
            word = words[i]
            if word in PRONUNCIATION_FIXES:
                fixed_words.append(PRONUNCIATION_FIXES[word])
            else:
                fixed_words.append(word)
            i += 1
    
    return ' '.join(fixed_words)


def apply_typo_corrections(text: str) -> str:
    """Fix common typos in the text."""
    words = text.lower().split()
    fixed_words = []
    
    for word in words:
        if word in TYPO_CORRECTIONS:
            fixed_words.append(TYPO_CORRECTIONS[word])
        else:
            fixed_words.append(word)
    
    return ' '.join(fixed_words)


def find_similar_song(query: str, threshold: float = 0.6) -> Optional[str]:
    """
    Find the most similar song title from our database.
    Uses difflib for fuzzy matching.
    
    Args:
        query: The search query (potentially mispronounced)
        threshold: Minimum similarity ratio (0.0 to 1.0)
    
    Returns:
        Best matching song title or None if no match above threshold
    """
    query = normalize_text(query)
    
    best_match = None
    best_ratio = 0.0
    
    for song in POPULAR_SONGS:
        ratio = difflib.SequenceMatcher(None, query, song.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = song
    
    return best_match


def get_close_matches_with_scores(query: str, n: int = 3) -> List[Tuple[str, float]]:
    """
    Get close matches with their similarity scores.
    
    Args:
        query: Search query
        n: Number of matches to return
    
    Returns:
        List of (song_title, similarity_score) tuples
    """
    query = normalize_text(query)
    
    matches = []
    for song in POPULAR_SONGS:
        ratio = difflib.SequenceMatcher(None, query, song.lower()).ratio()
        matches.append((song, ratio))
    
    # Sort by ratio descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches[:n]


def correct_english_query(query: str) -> str:
    """
    Main function to correct an English song query.
    
    Process:
    1. Apply pronunciation fixes (Vietnamese -> English)
    2. Apply typo corrections
    3. Try fuzzy matching with popular songs
    4. Return best corrected version
    
    Args:
        query: Original voice input query
    
    Returns:
        Corrected query for better YouTube search
    """
    original = query
    
    # Step 1: Apply pronunciation fixes
    corrected = apply_pronunciation_fixes(query)
    
    # Step 2: Apply typo corrections
    corrected = apply_typo_corrections(corrected)
    
    # Step 3: Try fuzzy matching
    similar_song = find_similar_song(corrected, threshold=0.65)
    
    if similar_song:
        # If we found a very close match, use it
        print(f"[CORRECTOR] Matched '{original}' -> '{similar_song}'")
        return similar_song
    
    # If no exact match found, return the corrected version
    if corrected != original:
        print(f"[CORRECTOR] Corrected '{original}' -> '{corrected}'")
    
    return corrected


def get_query_variations(query: str) -> List[str]:
    """
    Generate multiple variations of a query for better search.
    Useful when one search fails.
    
    Args:
        query: Original query
    
    Returns:
        List of query variations to try
    """
    variations = []
    
    # Original corrected version
    corrected = correct_english_query(query)
    variations.append(corrected)
    
    # Add "song" if not present
    if "song" not in corrected.lower():
        variations.append(f"{corrected} song")
    
    # Add "lyrics" version
    variations.append(f"{corrected} lyrics")
    
    # Original with typo fixes only
    typo_fixed = apply_typo_corrections(query)
    if typo_fixed != corrected:
        variations.append(typo_fixed)
    
    # Original with pronunciation fixes only
    pron_fixed = apply_pronunciation_fixes(query)
    if pron_fixed != corrected and pron_fixed != typo_fixed:
        variations.append(pron_fixed)
    
    # Get close song matches
    top_matches = get_close_matches_with_scores(corrected, n=2)
    for song, score in top_matches:
        if score > 0.5 and song not in variations:
            variations.append(song)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    return unique_variations


# ============================================
# PHONETIC PATTERNS (Metaphone-like simple version)
# ============================================
def simplify_phonetically(word: str) -> str:
    """
    Simplify a word phonetically for comparison.
    This is a simple version inspired by Metaphone algorithm.
    """
    word = word.lower()
    
    # Common phonetic substitutions
    substitutions = [
        (r'ph', 'f'),
        (r'ck', 'k'),
        (r'sh', 's'),
        (r'ch', 'c'),
        (r'th', 't'),
        (r'wh', 'w'),
        (r'ght', 't'),
        (r'ough', 'o'),
        (r'augh', 'af'),
        (r'tion', 'sn'),
        (r'sion', 'sn'),
        (r'ance|ence', 'ns'),
        (r'([aeiou])\1+', r'\1'),  # Remove duplicate vowels
        (r'([^aeiou])\1+', r'\1'),  # Remove duplicate consonants
        (r'e$', ''),  # Silent e at end
        (r'y$', 'i'),  # y sounds like i at end
    ]
    
    for pattern, replacement in substitutions:
        word = re.sub(pattern, replacement, word)
    
    return word


def phonetic_match(word1: str, word2: str) -> float:
    """
    Compare two words phonetically.
    Returns similarity score 0.0 to 1.0
    """
    p1 = simplify_phonetically(word1)
    p2 = simplify_phonetically(word2)
    
    return difflib.SequenceMatcher(None, p1, p2).ratio()
