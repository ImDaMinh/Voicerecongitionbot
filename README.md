# 🌙 Luna - Discord Voice Recognition Music Bot

Bot Discord phát nhạc điều khiển bằng **giọng nói** và **lệnh text**, hỗ trợ cả tiếng Việt và tiếng Anh.

## ✨ Tính năng

### 🎤 Điều khiển giọng nói
- **Song ngữ**: Nhận diện tiếng Việt & tiếng Anh đồng thời
- **Wake word "Luna"**: Ngăn kích hoạt nhầm
- **Chống spam**: Cooldown, lọc duplicate, rate limiting

### 🎶 Phát nhạc
- **YouTube & Spotify**: Hỗ trợ playlist từ cả hai nền tảng
- **Lazy loading**: Tải bài khi sắp phát để thêm playlist nhanh
- **Tìm kiếm thông minh**: Tự sửa lỗi phiên âm tiếng Anh

### 🛡️ Lọc nội dung
- Chặn từ ngữ không phù hợp (Việt/Anh)
- Phát hiện spam và request vô nghĩa

---

## 🎮 Lệnh

### Giọng nói (Wake word: "Luna")
| Lệnh | Mô tả |
|------|-------|
| `Luna play [tên bài]` | Phát bài hát |
| `Luna mở bài [tên bài]` | Phát bài hát |
| `Luna skip` | Chuyển bài |
| `Luna chuyển bài` | Chuyển bài |
| `Luna bài hiện tại` | Xem bài đang phát |
| `Luna ngắt kết nối` | Ngắt kết nối bot |

### Text (Prefix: `l`)
| Lệnh | Alias | Mô tả |
|------|-------|-------|
| `ljoin` | | Vào voice channel |
| `lplay <bài>` | `lp` | Phát bài hát |
| `lplay <URL>` | `lp` | Phát playlist (YouTube/Spotify) |
| `lqueue` | `lq` | Xem hàng đợi |
| `lnowplaying` | `lnp` | Bài đang phát |
| `lskip` | `ls` | Chuyển bài |
| `lclear` | | Xóa hàng đợi |
| `lstop` | `ldc` | Dừng & rời kênh |
| `lhelp` | `lh` | Xem hướng dẫn |

---

## 🚀 Cài đặt

### Yêu cầu
- Python 3.8+
- FFmpeg (đã thêm vào PATH)
- Discord Bot Token

### Bước cài đặt

```bash
# 1. Clone repo
git clone https://github.com/ImDaMinh/Voicerecongitionbot.git
cd Voicerecongitionbot

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Tạo file .env
echo DISCORD_TOKEN=your_token_here > .env

# 4. (Tùy chọn) Thêm Spotify API để hỗ trợ playlist Spotify
# SPOTIFY_CLIENT_ID=your_client_id
# SPOTIFY_CLIENT_SECRET=your_client_secret

# 5. Chạy bot
python bot.py
```

---

## 📦 Dependencies

```
discord.py>=2.0.0
discord-ext-voice-recv
PyNaCl
SpeechRecognition
webrtcvad-wheels
yt-dlp
python-dotenv
beautifulsoup4
aiohttp
requests
```

---

## ⚙️ Cấu hình

Trong `voiceInput.py`:
```python
DEBUG_MODE = False       # Bật/tắt debug
SILENCE_THRESHOLD = 1.5  # Thời gian im lặng trước khi xử lý (giây)
MIN_AUDIO_LENGTH = 0.8   # Độ dài audio tối thiểu (giây)
RMS_THRESHOLD = 50       # Ngưỡng âm lượng
```

---

## 📂 Cấu trúc project

```
voicerecongitionbot/
├── bot.py               # Logic chính, xử lý lệnh
├── voiceInput.py        # Nhận diện giọng nói
├── music_player.py      # Phát nhạc, YouTube/Spotify
├── content_filter.py    # Lọc nội dung
├── english_corrector.py # Sửa lỗi phiên âm tiếng Anh
├── patch_opus.py        # Patch Opus codec
├── requirements.txt     # Dependencies
└── .env                 # Token (tự tạo)
```

---

## 💡 Tips

- Nói tên bài tiếng Anh bằng **phiên âm Việt** được!
- Thêm `remix`, `live`, `acoustic` để tìm bản khác
- Paste link **YouTube/Spotify playlist** để thêm nhiều bài

---

## 📝 License

MIT License

---

**Made with 💜 by ImDaMinh**
