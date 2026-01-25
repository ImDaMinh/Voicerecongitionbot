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

# 🎵 Add a song to the queue
async def add_to_queue(ctx, query, queue):
    try:
        # Just pass the query directly, let yt-dlp handle it via default_search
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in info:
            info = info['entries'][0]
            
        url = info['url']
        title = info['title']
        queue.append((url, title))
        await ctx.send(f"✅ Added to queue: **{title}**")
    except Exception as e:
        await ctx.send(f"❌ Failed to add song: {e}")

# ▶️ Start playing from the queue
async def start_playback(ctx, queue):
    if not queue or ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        return

    url, title = queue.pop(0)
    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    def after_play(_):
        asyncio.run_coroutine_threadsafe(start_playback(ctx, queue), ctx.bot.loop)

    ctx.voice_client.play(source, after=after_play)
    await ctx.send(f"🎶 Now playing: **{title}**")

