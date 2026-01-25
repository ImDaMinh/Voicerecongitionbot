# Discord Voice Recognition Bot

A Discord bot that listens to voice commands, plays music, and responds to wake words.

## Features
*   **Voice Recognition**: Listens for wake words like "Hello bot", "Alo bot", "Mở bài [song name]".
*   **Music Playback**: Plays music from YouTube using `yt-dlp`.
*   **Voice Commands**: Supports "Skip", "Stop", "Leave" via voice.
*   **Direct Song Request**: Say "Mở bài [song name]" to queue a song immediately.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You also need `ffmpeg` installed and added to your system PATH.*

2.  **Configuration**:
    Create a `.env` file in the root directory and add your Discord Bot Token:
    ```env
    DISCORD_TOKEN=your_token_here
    ```

3.  **Run the Bot**:
    ```bash
    python bot.py
    ```

## Usage
*   Join a voice channel.
*   Type `!join` or just start speaking if the bot is already in.
*   Say "Hello bot" to check if it's listening.
*   Say "Mở bài Sơn Tùng" to play music.
