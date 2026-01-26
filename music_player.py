import yt_dlp as youtube_dl
import asyncio
import discord

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -loglevel quiet -bufsize 64k -probesize 32k -ar 48000 -ac 2'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# 🎵 Track currently playing song info
_current_song_info = None

def format_duration(seconds):
    """Format duration in seconds to MM:SS or HH:MM:SS"""
    if seconds is None:
        return "Unknown"
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"

def get_current_song():
    """Returns info dict of the currently playing song, or None if nothing is playing."""
    return _current_song_info

# 🎵 Add a song to the queue
async def add_to_queue(ctx, query, queue):
    try:
        # Just pass the query directly, let yt-dlp handle it via default_search
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in info:
            info = info['entries'][0]
        
        # Store all needed info
        song_info = {
            'url': info['url'],
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader', 'Unknown'),
            'webpage_url': info.get('webpage_url', ''),
        }
        queue.append(song_info)
        await ctx.send(f"✅ Đã thêm vào hàng đợi: **{song_info['title']}**")
    except Exception as e:
        await ctx.send(f"❌ Không thể thêm bài: {e}")

# ▶️ Start playing from the queue
async def start_playback(ctx, queue):
    global _current_song_info
    
    if not queue or ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        return

    song_info = queue.pop(0)
    _current_song_info = song_info  # Track the current song
    source = discord.FFmpegPCMAudio(song_info['url'], **ffmpeg_options)

    def after_play(_):
        global _current_song_info
        _current_song_info = None  # Clear when song ends
        asyncio.run_coroutine_threadsafe(start_playback(ctx, queue), ctx.bot.loop)

    ctx.voice_client.play(source, after=after_play)
    
    # Create a beautiful embed for now playing
    embed = discord.Embed(
        title="🎶 Đang phát",
        description=f"**[{song_info['title']}]({song_info['webpage_url']})**",
        color=discord.Color.from_rgb(255, 0, 127)  # Pink color
    )
    if song_info['thumbnail']:
        embed.set_thumbnail(url=song_info['thumbnail'])
    embed.add_field(name="👤 Nghệ sĩ", value=song_info['uploader'], inline=True)
    embed.add_field(name="⏱️ Thời lượng", value=format_duration(song_info['duration']), inline=True)
    embed.set_footer(text="🎧 Nói 'bài hiện tại' để xem lại thông tin bài hát")
    
    await ctx.send(embed=embed)
