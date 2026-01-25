import patch_opus
import discord
from discord.ext import commands
from discord.ext import voice_recv
from voiceInput import setup_sink, get_next_phrase
from music_player import add_to_queue, start_playback
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

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        setup_sink(vc, bot)
        await ctx.send("🎤 Listening... Say 'hello bot'or''music bot' to wake me up!")

        while True:
            wake_text = await get_next_phrase()

            wake_phrases = ["hello","hello bot","alo bot","alo","music bot","alopos","nhạc","music","mở nhạc","trái cam","mở bài","play music"]
            spoken = wake_text.lower()

            # wake_phrases = ["hello","hello bot","alo bot","alo","music bot","alopos","nhạc","music","mở nhạc","trái cam","mở bài","play music"]
            # Sort by length desc to match longest phrase first
            sorted_wake_phrases = sorted(wake_phrases, key=len, reverse=True)
            
            matched_wake = None
            for p in sorted_wake_phrases:
                if p in spoken:
                    matched_wake = p
                    break

            if matched_wake:
                await ctx.send("👂 I'm listening! (You have 10 seconds to say a command...)")

                # Check if there is a command included with the wake word
                # e.g. "mở bài sơn tùng" -> matched "mở bài", remainder "sơn tùng"
                initial_command = None
                if spoken.startswith(matched_wake):
                    remainder = spoken[len(matched_wake):].strip()
                    if remainder:
                        initial_command = remainder
                
                # 🔊 Pick a random WAV from your folder
                voice_files = ["voice1.wav", "voice2.wav", "voice3.wav"]
                chosen_file = random.choice(voice_files)

                # 🔊 Play it into VC
                if ctx.voice_client and not ctx.voice_client.is_playing():
                    source = discord.FFmpegPCMAudio(chosen_file)
                    ctx.voice_client.play(source)
                await ctx.send("🎙 Speak now...")

                # Start a timer window for next command
                start_time = asyncio.get_event_loop().time()
                
                # If we have an initial command, process it immediately in the loop
                first_pass = True
                
                while asyncio.get_event_loop().time() - start_time < 10:
                    try:
                        if first_pass and initial_command:
                            command_text = initial_command
                            # Don't set first_pass = False here, we want to treat it as if we just received it
                            # But we need to make sure we don't loop infinitely if we don't break
                            # The logic below breaks on success, so it's fine.
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
                    
                    # Check for control commands first
                    if spoken_cmd in ["leave", "stop", "exit", "thoát", "cút"]:
                        await ctx.send("👋 Voice session ended.")
                        await ctx.voice_client.disconnect()
                        song_queue.clear()
                        return

                    elif spoken_cmd in ["skip", "next", "bỏ qua"]:
                        if ctx.voice_client and ctx.voice_client.is_playing():
                            ctx.voice_client.stop_playing()
                            await ctx.send("⏭️ Skipping...")
                        else:
                            await ctx.send("❌ Nothing playing.")
                            
                    # If not a control command, assume it's a song request
                    else:
                        # Remove any accidental trigger words if user still says them
                        # e.g. "play music son tung" -> "son tung"
                        # But if they just say "son tung", it works too.
                        trigger_words = ["play music", "phát nhạc", "mở bài", "bật bài", "play bài", "mở", "play"]
                        song_query = spoken_cmd
                        
                        for trigger in trigger_words:
                            if spoken_cmd.startswith(trigger):
                                song_query = spoken_cmd.replace(trigger, "", 1).strip()
                                break
                        
                        if not song_query:
                             await ctx.send("❌ I heard the trigger but no song name.")
                             continue

                        # 🔊 Play confirmation voice line (voice4 or voice5)
                        music_lines = ["voice4.wav", "voice5.wav"]
                        music_voice = random.choice(music_lines)

                        # Only play confirmation if nothing is playing (to avoid talking over music)
                        if ctx.voice_client and not ctx.voice_client.is_playing():
                            source = discord.FFmpegPCMAudio(music_voice)
                            ctx.voice_client.play(source)
                            # We can wait a bit if we just started playing the voice line, 
                            # but it's better to just proceed to queueing.
                            # If we really want to wait for the voice line, we'd need to track if we *just* started it.
                            # For now, removing the blocking wait is the priority.
                            await asyncio.sleep(1.0) # Short wait for voice line to start/finish

                        # ▶️ Now queue and play the song
                        await add_to_queue(ctx, song_query, song_queue)
                        await start_playback(ctx, song_queue)
                        break
            else:
                print(f"[DEBUG] Ignored wake attempt: '{wake_text}'")

            await asyncio.sleep(1.0)  # prevent loop spam


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
