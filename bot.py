import patch_opus
import discord
from discord.ext import commands
from discord.ext import voice_recv
from voiceInput import setup_sink, get_next_phrase
from music_player import add_to_queue, start_playback, get_current_song
import asyncio
import difflib
import random
import os
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 🔁 Song queue
song_queue = []

# 🎵 Currently playing song title
current_song = None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        current_sink = setup_sink(vc, bot)
        await ctx.send("🎤 Listening... Say 'Luna + tên bài hát' để bật nhạc!")

        while True:
            wake_text = await get_next_phrase()
            spoken = wake_text.lower().strip()

            # ============================================
            # DIRECT CONTROL COMMANDS (no wake phrase needed)
            # These work anytime, even while music is playing
            # ============================================
            
            # Check for leave/stop commands
            if spoken in ["ngắt kết nối"]:
                await ctx.send("👋 Đã kết thúc phiên nghe nhạc.")
                await ctx.voice_client.disconnect()
                song_queue.clear()
                return

            # Check for skip commands
            if spoken in ["chuyển bài","luna skip"]:
                print(f"[DEBUG] Skip command detected: '{spoken}'")
                if ctx.voice_client and ctx.voice_client.is_playing():
                    print("[DEBUG] Stopping current track...")
                    ctx.voice_client.stop()
                    await ctx.send("⏭️ Đang chuyển bài...")
                    # Wait for the audio to finish stopping
                    await asyncio.sleep(0.5)
                    # Re-setup listener to ensure voice recognition continues
                    print("[DEBUG] Re-setting up voice listener...")
                    current_sink = setup_sink(vc, bot)
                    await asyncio.sleep(1.0)
                    print("[DEBUG] Skip complete, listener reset, resuming voice recognition loop")
                else:
                    await ctx.send("❌ Không có bài nào đang phát.")
                print("[DEBUG] Continuing main loop after skip...")
                continue

            # Check for now playing commands
            if spoken in ["bài hiện tại"]:
                song_info = get_current_song()
                if song_info:
                    from music_player import format_duration
                    embed = discord.Embed(
                        title="🎵 Đang phát",
                        description=f"**[{song_info['title']}]({song_info['webpage_url']})**",
                        color=discord.Color.from_rgb(30, 215, 96)  # Spotify green
                    )
                    if song_info.get('thumbnail'):
                        embed.set_thumbnail(url=song_info['thumbnail'])
                    embed.add_field(name="👤 Nghệ sĩ", value=song_info.get('uploader', 'Unknown'), inline=True)
                    embed.add_field(name="⏱️ Thời lượng", value=format_duration(song_info.get('duration')), inline=True)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Không có bài nào đang phát.")
                await asyncio.sleep(0.5)
                continue

            # ============================================
            # WAKE PHRASE DETECTION (for playing new songs)
            # ============================================
            wake_phrases = ["luna"]
            
            # Sort by length desc to match longest phrase first
            sorted_wake_phrases = sorted(wake_phrases, key=len, reverse=True)
            
            matched_wake = None
            for p in sorted_wake_phrases:
                if p in spoken:
                    matched_wake = p
                    break

            if matched_wake:
                # Check if there is a command included with the wake word
                # e.g. "mở bài sơn tùng" -> matched "mở bài", remainder "sơn tùng"
                initial_command = None
                if spoken.startswith(matched_wake):
                    remainder = spoken[len(matched_wake):].strip()
                    if remainder:
                        initial_command = remainder
                
                # Start a timer window for next command
                start_time = asyncio.get_event_loop().time()
                
                # If we have an initial command, process it immediately in the loop
                first_pass = True
                
                while asyncio.get_event_loop().time() - start_time < 10:
                    try:
                        if first_pass and initial_command:
                            command_text = initial_command
                        else:
                            command_text = await asyncio.wait_for(get_next_phrase(), timeout=10.0)
                        
                        first_pass = False
                    except asyncio.TimeoutError:
                        break
                    except Exception as e:
                        print(f"[ERROR] Command listen error: {e}")
                        break

                    if not command_text.strip():
                        continue

                    spoken_cmd = command_text.lower()
                    
                    # Check for control commands inside the command window too
                    if spoken_cmd in ["leave", "stop", "exit", "thoát", "cút"]:
                        await ctx.send("👋 Đã kết thúc phiên nghe nhạc.")
                        await ctx.voice_client.disconnect()
                        song_queue.clear()
                        return

                    elif spoken_cmd in ["skip", "next", "bỏ qua", "qua bài", "bài tiếp", "tiếp"]:
                        if ctx.voice_client and ctx.voice_client.is_playing():
                            ctx.voice_client.stop()
                            await ctx.send("⏭️ Đang chuyển bài...")
                        else:
                            await ctx.send("❌ Không có bài nào đang phát.")
                        continue

                    elif spoken_cmd in ["now playing", "đang phát", "bài gì", "đang nghe gì", "what song", "this song", "bài này là gì"]:
                        current = get_current_song()
                        if current:
                            await ctx.send(f"🎵 Đang phát: **{current}**")
                        else:
                            await ctx.send("❌ Không có bài nào đang phát.")
                        continue
                            
                    # If not a control command, assume it's a song request
                    else:
                        # Remove any accidental trigger words if user still says them
                        trigger_words = ["play music", "phát nhạc", "mở bài", "bật bài", "play bài", "mở", "play"]
                        song_query = spoken_cmd                        
                        for trigger in trigger_words:
                            if spoken_cmd.startswith(trigger):
                                song_query = spoken_cmd.replace(trigger, "", 1).strip()
                                break
                        
                        if not song_query:
                             continue

                        # ▶️ Now queue and play the song
                        await add_to_queue(ctx, song_query, song_queue)
                        await start_playback(ctx, song_queue)
                        break
            else:
                print(f"[DEBUG] Ignored: '{wake_text}'")

            await asyncio.sleep(0.5)  # prevent loop spam


    else:
        await ctx.send("❌ You're not in a voice channel.")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop_playing()
        await ctx.send("⏭️ Skipping current track...")

@bot.command()
async def queue(ctx):
    if song_queue:
        msg = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(song_queue)])
        await ctx.send(f"📃 Current Queue:\n{msg}")
    else:
        await ctx.send("📭 Queue is empty.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        song_queue.clear()
        await ctx.send("👋 Left the voice channel and cleared the queue.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("❌ Error: DISCORD_TOKEN not found in .env file.")
else:
    bot.run(TOKEN)
