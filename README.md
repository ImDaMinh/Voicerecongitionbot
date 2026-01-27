# 🎵 Luna - Discord Voice Recognition Music Bot

A powerful Discord bot that listens to voice commands in both Vietnamese and English, plays music from YouTube, and provides intelligent content filtering.

## ✨ Features

### 🎤 Voice Recognition
- **Dual-language support**: Recognizes both Vietnamese (vi-VN) and English (en-US) simultaneously
- **Wake word activation**: Uses "Luna" as the wake word to prevent accidental triggers
- **Smart audio processing**: 
  - Configurable silence detection and RMS threshold
  - Anti-overload protection with cooldown system
  - Duplicate command filtering
  - Rate limiting to prevent spam

### 🎶 Music Playback
- **YouTube integration**: Plays music directly from YouTube using `yt-dlp`
- **Intelligent search**: 
  - Automatic English query correction for better search results
  - Multiple search variations to find the right song
  - Supports Vietnamese and English song names
- **Rich embeds**: Beautiful Discord embeds showing song info, thumbnail, artist, and duration
- **Queue system**: Add multiple songs to the queue

### 🛡️ Content Filtering
- **Profanity filter**: Blocks inappropriate words in Vietnamese and English
- **Spam protection**: Detects and blocks nonsensical or spam requests
- **Smart validation**: Uses heuristics to identify valid song requests

### 🎮 Voice Commands

#### Music Control (Wake word required: "Luna")
- `Luna play [song name]` - Play a song
- `Luna skip` / `Luna chuyển bài` - Skip current song
- `Luna bài hiện tại` / `Luna now playing` - Show current song info
- `Luna ngắt kết nối` / `Luna disconnect` - Disconnect bot from voice channel

#### Text Commands
- `!join` - Bot joins your voice channel and starts listening
- `!skip` - Skip the current song
- `!queue` - Show the current song queue
- `!leave` - Bot leaves the voice channel

## 🚀 Setup

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed and added to system PATH
- Discord Bot Token

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ImDaMinh/Voicerecongitionbot.git
   cd Voicerecongitionbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

## 📋 Requirements

- `discord.py` - Discord API wrapper
- `discord-ext-voice-recv` - Voice receiving extension
- `yt-dlp` - YouTube downloader
- `python-dotenv` - Environment variable management
- `SpeechRecognition` - Speech recognition library
- `PyNaCl` - Voice encryption support

## 🎯 Usage Example

1. Join a voice channel in Discord
2. Type `!join` in a text channel
3. Wait for the bot to join and start listening
4. Say: **"Luna play despacito"** or **"Luna play see tình"**
5. The bot will search for and play the song
6. Use **"Luna skip"** to skip to the next song
7. Use **"Luna bài hiện tại"** to see what's currently playing

## 🔧 Configuration

You can adjust the voice recognition settings in `voiceInput.py`:

```python
DEBUG_MODE = False          # Enable/disable debug messages
SILENCE_THRESHOLD = 1.5     # Silence duration before processing (seconds)
MIN_AUDIO_LENGTH = 0.8      # Minimum audio length to process (seconds)
RMS_THRESHOLD = 50          # Volume threshold for voice detection
```

## 🏗️ Project Structure

```
voicerecongitionbot/
├── bot.py                  # Main bot logic and command handling
├── voiceInput.py          # Voice recognition and audio processing
├── music_player.py        # Music playback and YouTube integration
├── content_filter.py      # Content filtering and validation
├── english_corrector.py   # English query correction
├── patch_opus.py          # Opus codec patching
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (create this)
```

## 🎨 Features in Detail

### Anti-Overload Protection
- Command cooldown system (2 seconds between commands)
- Processing lock to prevent concurrent command execution
- Duplicate command detection within 5-second window

### Smart Language Detection
- Prioritizes Vietnamese for control commands (skip, disconnect, etc.)
- Prioritizes English for song names
- Runs both language recognitions in parallel for speed

### Content Safety
- Blacklist of inappropriate words in multiple languages
- Validation for song name length and format
- Detection of spam patterns and excessive character repetition

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Music powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Voice recognition using Google Speech Recognition API

---

**Made with ❤️ by ImDaMinh**
