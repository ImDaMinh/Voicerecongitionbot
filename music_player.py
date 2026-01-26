import yt_dlp as youtube_dl
import asyncio
import discord
from english_corrector import correct_english_query, get_query_variations

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
    # Step 1: Correct the query using english_corrector
    original_query = query
    corrected_query = correct_english_query(query)
    
    # Get all variations to try
    query_variations = get_query_variations(query)
    
    print(f"[SEARCH] Original: '{original_query}'")
    print(f"[SEARCH] Corrected: '{corrected_query}'")
    print(f"[SEARCH] Will try variations: {query_variations}")
    
    last_error = None
    
    # Try each variation until one works
    for variation in query_variations:
        try:
            print(f"[SEARCH] Trying: '{variation}'")
            
            # Pass the query directly, let yt-dlp handle it via default_search
            info = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda v=variation: ytdl.extract_info(v, download=False)
            )
            
            if info is None:
                print(f"[SEARCH] No results for '{variation}'")
                continue
            
            if 'entries' in info:
                if not info['entries']:
                    print(f"[SEARCH] Empty entries for '{variation}'")
                    continue
                info = info['entries'][0]
            
            # Success! Store all needed info
            song_info = {
                'url': info['url'],
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader', 'Unknown'),
                'webpage_url': info.get('webpage_url', ''),
            }
            queue.append(song_info)
            
            # Show what we searched for if it was corrected
            if variation != original_query:
                await ctx.send(f"🔍 Đã tìm: **{variation}** (từ '{original_query}')")
            
            await ctx.send(f"✅ Đã thêm vào hàng đợi: **{song_info['title']}**")
            return  # Success, exit the function
            
        except Exception as e:
            print(f"[SEARCH] Failed for '{variation}': {e}")
            last_error = e
            continue  # Try next variation
    
    # All variations failed
    await ctx.send(f"❌ Không tìm thấy bài hát: {original_query}")
    if last_error:
        print(f"[SEARCH] Last error: {last_error}")

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
