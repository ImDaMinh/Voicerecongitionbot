import patch_opus
import discord
import logging

# 🔇 Suppress noisy voice_recv logs (RTCP packets, unknown ssrc, etc.)
logging.getLogger('discord.ext.voice_recv.reader').setLevel(logging.WARNING)
logging.getLogger('discord.ext.voice_recv.gateway').setLevel(logging.WARNING)
logging.getLogger('discord.ext.voice_recv.opus').setLevel(logging.WARNING)
from discord.ext import commands
from discord.ext import voice_recv
from voiceInput import setup_sink, get_next_phrase, lock_user, unlock_user
from music_player import add_to_queue, start_playback, get_current_song, add_playlist_to_queue
from content_filter import filter_song_request
import asyncio
import difflib
import random
import os
import time
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="l", intents=intents, help_command=None)

# 🔁 Song queue
song_queue = []

# 🎵 Currently playing song title
current_song = None

# 🛡️ Anti-overload protection
_last_command_time = 0
_command_cooldown = 2.0  # seconds between commands
_is_processing = False
_last_processed_text = ""
_last_skip_time = 0  # Anti-duplicate for skip commands

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        current_sink = setup_sink(vc, bot)
        await ctx.send("🎤 Listening... Nói 'Lunaplay + tên bài' hoặc 'Luna mở bài + tên bài' để bật nhạc!")

        while True:
            global _last_command_time, _is_processing, _last_processed_text
            
            wake_text = await get_next_phrase()
            spoken = wake_text.lower().strip()
            
            # 🛡️ ANTI-OVERLOAD: Skip if we're still processing or in cooldown
            current_time = time.time()
            if _is_processing:
                print(f"[OVERLOAD] Skipping '{spoken[:30]}...' - still processing previous command")
                continue
            
            if current_time - _last_command_time < _command_cooldown:
                print(f"[COOLDOWN] Skipping '{spoken[:30]}...' - cooldown active")
                continue
            
            # 🛡️ Skip duplicate commands within short time
            if spoken == _last_processed_text and current_time - _last_command_time < 5.0:
                print(f"[DUPLICATE] Skipping duplicate command: '{spoken[:30]}...'")
                continue

            # ============================================
            # DIRECT CONTROL COMMANDS (with or without Luna wake word)
            # These work anytime, even while music is playing
            # ============================================
            
            # Define control command patterns (ALL require Luna wake word)
            disconnect_commands = ["luna ngắt kết nối", "luna disconnect"]
            skip_commands = ["luna skip", "luna chuyển bài", "luna bỏ qua"]
            now_playing_commands = ["luna bài hiện tại", "luna now playing"]
            
            # Check for leave/stop commands
            if spoken in disconnect_commands:
                await ctx.send("👋 Đã kết thúc phiên nghe nhạc.")
                await ctx.voice_client.disconnect()
                song_queue.clear()
                return

            # Check for skip commands
            if spoken in skip_commands:
                print(f"[DEBUG] Skip command detected: '{spoken}'")
                
                # Anti-duplicate: prevent multiple skip commands within 3 seconds
                if current_time - _last_skip_time < 3.0:
                    print(f"[SKIP] Ignoring duplicate skip command (within 3s cooldown)")
                    continue
                
                # Check if there's something to skip (playing OR has queue)
                has_music = ctx.voice_client and (ctx.voice_client.is_playing() or song_queue)
                
                if has_music:
                    _last_skip_time = current_time  # Update last skip time
                    print("[DEBUG] Stopping current track...")
                    if ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                    await ctx.send("⏭️ Đang chuyển bài...")
                    # Wait for the audio to finish stopping
                    await asyncio.sleep(0.5)
                    # Re-setup listener to ensure voice recognition continues
                    print("[DEBUG] Re-setting up voice listener...")
                    current_sink = setup_sink(vc, bot, force_restart=True)
                    await asyncio.sleep(1.0)
                    print("[DEBUG] Skip complete, listener reset, resuming voice recognition loop")
                else:
                    await ctx.send("❌ Không có bài nào đang phát.")
                print("[DEBUG] Continuing main loop after skip...")
                continue

            # Check for now playing commands
            if spoken in now_playing_commands:
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
            wake_phrases = ["luna play", "luna mở bài"]
            
            # Sort by length desc to match longest phrase first
            sorted_wake_phrases = sorted(wake_phrases, key=len, reverse=True)
            
            matched_wake = None
            for p in sorted_wake_phrases:
                if p in spoken:
                    matched_wake = p
                    break

            if matched_wake:
                # 🛡️ Set processing lock
                _is_processing = True
                _last_command_time = time.time()
                _last_processed_text = spoken
                
                # 🔒 Lock to this user only (priority system)
                lock_user(ctx.author.id)
                
                try:
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
                            # Check if there's something to skip (playing OR has queue)
                            has_music = ctx.voice_client and (ctx.voice_client.is_playing() or song_queue)
                            
                            if has_music:
                                if ctx.voice_client.is_playing():
                                    ctx.voice_client.stop()
                                await ctx.send("⏭️ Đang chuyển bài...")
                                # Re-setup voice listener
                                await asyncio.sleep(0.5)
                                setup_sink(vc, bot, force_restart=True)
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

                            # 🛡️ Content filter check
                            is_allowed, filter_reason = filter_song_request(song_query)
                            if not is_allowed:
                                await ctx.send(f"❌ {filter_reason}")
                                print(f"[FILTER] Blocked: '{song_query}' - {filter_reason}")
                                break

                            # ▶️ Now queue and play the song
                            await add_to_queue(ctx, song_query, song_queue)
                            await start_playback(ctx, song_queue)
                            # Re-setup voice listener after starting playback
                            await asyncio.sleep(0.5)
                            setup_sink(vc, bot, force_restart=True)
                            break
                finally:
                    # 🛡️ Release processing lock
                    _is_processing = False
                    _last_command_time = time.time()
                    # 🔓 Unlock user priority
                    unlock_user()
            else:
                print(f"[DEBUG] Ignored: '{wake_text}'")
            await asyncio.sleep(0.5)  # prevent loop spam


    else:
        await ctx.send("❌ You're not in a voice channel.")

# ============================================
# MANUAL TEXT COMMANDS (prefix: l)
# ============================================

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query: str = None):
    """Play a song by text command. Usage: lplay <song name>"""
    if not query:
        await ctx.send("❌ Bạn cần nhập tên bài hát. Ví dụ: `lplay shape of you`")
        return
    
    # Join voice channel if not already connected
    if not ctx.voice_client:
        if ctx.author.voice:
            vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
            await asyncio.sleep(0.5)  # Wait for voice client to be ready
            print(f"[DEBUG] Connected to voice channel, voice_client ready: {ctx.voice_client is not None}")
        else:
            await ctx.send("❌ Bạn cần vào voice channel trước!")
            return
    
    # 🎵 Check if it's a playlist URL (YouTube, YouTube Music, or Spotify)
    is_playlist = (
        'list=' in query or 
        '/playlist?' in query or 
        'spotify.com/playlist' in query or
        'open.spotify.com/playlist' in query or
        'music.youtube.com' in query
    )
    
    if is_playlist:
        print(f"[DEBUG] Detected playlist URL: {query}")
        added = await add_playlist_to_queue(ctx, query, song_queue)
        if added > 0:
            await start_playback(ctx, song_queue)
            # Re-setup voice listener after starting playback
            await asyncio.sleep(0.5)
            if ctx.voice_client:
                setup_sink(ctx.voice_client, bot)
        return
    
    # Filter content (only for non-playlist queries)
    is_allowed, filter_reason = filter_song_request(query)
    if not is_allowed:
        await ctx.send(f"❌ {filter_reason}")
        return
    
    # Add to queue and play
    print(f"[DEBUG] Adding to queue: {query}")
    await add_to_queue(ctx, query, song_queue)
    print(f"[DEBUG] Queue after add: {len(song_queue)} items")
    print(f"[DEBUG] Voice client playing: {ctx.voice_client.is_playing() if ctx.voice_client else 'No VC'}")
    await start_playback(ctx, song_queue)
    # Re-setup voice listener after starting playback
    await asyncio.sleep(0.5)
    if ctx.voice_client:
        setup_sink(ctx.voice_client, bot)
    print(f"[DEBUG] After start_playback, playing: {ctx.voice_client.is_playing() if ctx.voice_client else 'No VC'}")

@bot.command(name='skip', aliases=['s', 'next'])
async def skip(ctx):
    """Skip the current song. Usage: lskip"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Đang chuyển bài...")
        # Re-setup voice listener after skip
        await asyncio.sleep(0.5)
        setup_sink(ctx.voice_client, bot, force_restart=True)
        await asyncio.sleep(0.5)
    else:
        await ctx.send("❌ Không có bài nào đang phát.")

@bot.command(name='queue', aliases=['q'])
async def queue(ctx):
    """Show the current queue. Usage: lqueue"""
    from music_player import format_duration, get_current_song
    
    if not song_queue and not get_current_song():
        embed = discord.Embed(
            title="📭 Hàng đợi trống",
            description="Dùng `lplay <tên bài>` để thêm nhạc!",
            color=discord.Color.light_grey()
        )
        await ctx.send(embed=embed)
        return
    
    # Calculate pagination
    songs_per_page = 10
    total_pages = max(1, (len(song_queue) + songs_per_page - 1) // songs_per_page)
    
    def create_queue_embed(page: int) -> discord.Embed:
        """Create embed for a specific page"""
        embed = discord.Embed(
            title="🎵 Hàng đợi nhạc",
            color=discord.Color.from_rgb(255, 0, 127)  # Pink
        )
        
        # Show currently playing
        current = get_current_song()
        if current:
            current_duration = format_duration(current.get('duration'))
            embed.add_field(
                name="▶️ Đang phát",
                value=f"**[{current['title']}]({current.get('webpage_url', '')})**\n👤 {current.get('uploader', 'Unknown')} • ⏱️ {current_duration}",
                inline=False
            )
        
        # Show queue for current page
        if song_queue:
            start_idx = page * songs_per_page
            end_idx = min(start_idx + songs_per_page, len(song_queue))
            
            queue_text = ""
            for i in range(start_idx, end_idx):
                song_info = song_queue[i]
                if isinstance(song_info, dict):
                    title = song_info.get('title', 'Unknown')
                    duration = format_duration(song_info.get('duration'))
                    if len(title) > 45:
                        title = title[:42] + "..."
                    queue_text += f"`{i+1}.` **{title}** ({duration})\n"
                else:
                    queue_text += f"`{i+1}.` {song_info}\n"
            
            # Calculate total duration
            total_seconds = sum(s.get('duration', 0) or 0 for s in song_queue)
            total_duration = format_duration(total_seconds) if total_seconds > 0 else "?"
            
            embed.add_field(
                name=f"📋 Tiếp theo ({len(song_queue)} bài)",
                value=queue_text if queue_text else "*Không có bài nào*",
                inline=False
            )
            
            embed.set_footer(text=f"📄 Trang {page + 1}/{total_pages} • ⏱️ Tổng: {total_duration}")
        else:
            embed.add_field(
                name="📋 Tiếp theo",
                value="*Không có bài nào trong queue*",
                inline=False
            )
        
        return embed
    
    # Create View with pagination buttons
    class QueueView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)
            self.current_page = 0
            self.update_buttons()
        
        def update_buttons(self):
            self.first_btn.disabled = self.current_page == 0
            self.prev_btn.disabled = self.current_page == 0
            self.next_btn.disabled = self.current_page >= total_pages - 1
            self.last_btn.disabled = self.current_page >= total_pages - 1
            self.page_btn.label = f"📄 {self.current_page + 1}/{total_pages}"
        
        @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
        async def first_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = 0
            self.update_buttons()
            await interaction.response.edit_message(embed=create_queue_embed(self.current_page), view=self)
        
        @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
        async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = max(0, self.current_page - 1)
            self.update_buttons()
            await interaction.response.edit_message(embed=create_queue_embed(self.current_page), view=self)
        
        @discord.ui.button(label="📄 1/1", style=discord.ButtonStyle.secondary, disabled=True)
        async def page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            pass  # This button just shows page info
        
        @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
        async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = min(total_pages - 1, self.current_page + 1)
            self.update_buttons()
            await interaction.response.edit_message(embed=create_queue_embed(self.current_page), view=self)
        
        @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
        async def last_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = total_pages - 1
            self.update_buttons()
            await interaction.response.edit_message(embed=create_queue_embed(self.current_page), view=self)
        
        async def on_timeout(self):
            # Disable all buttons on timeout
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    # Only show pagination if more than 1 page
    if total_pages > 1:
        view = QueueView()
        view.message = await ctx.send(embed=create_queue_embed(0), view=view)
    else:
        await ctx.send(embed=create_queue_embed(0))

@bot.command(name='nowplaying', aliases=['np', 'now'])
async def nowplaying(ctx):
    """Show the current playing song. Usage: lnowplaying or lnp"""
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
        embed.add_field(name="� Nghệ sĩ", value=song_info.get('uploader', 'Unknown'), inline=True)
        embed.add_field(name="⏱️ Thời lượng", value=format_duration(song_info.get('duration')), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Không có bài nào đang phát.")

@bot.command(name='stop', aliases=['leave', 'disconnect', 'dc'])
async def stop(ctx):
    """Stop playing and leave the voice channel. Usage: lstop"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        song_queue.clear()
        await ctx.send("👋 Đã dừng phát nhạc và rời kênh.")
    else:
        await ctx.send("❌ Bot không ở trong voice channel.")

@bot.command(name='clear', aliases=['c'])
async def clear(ctx):
    """Clear the queue. Usage: lclear"""
    song_queue.clear()
    await ctx.send("🗑️ Đã xóa hàng đợi.")

@bot.command(name='help', aliases=['h'])
async def help_cmd(ctx):
    """Show help message. Usage: lhelp or lh"""
    embed = discord.Embed(
        title="🌙 Luna Music Bot",
        description="**Bot phát nhạc điều khiển bằng giọng nói & lệnh text**\n━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.from_rgb(138, 43, 226)  # Violet
    )
    
    # Voice Commands Section
    embed.add_field(
        name="🎤 **ĐIỀU KHIỂN GIỌNG NÓI**",
        value=(
            "```\n"
            "🎵 Phát nhạc:\n"
            "   「Luna play + tên bài」\n"
            "   「Luna mở bài + tên bài」\n"
            "\n"
            "⏭️ Chuyển bài:  「Luna skip」\n"
            "🎵 Bài hiện tại: 「Luna bài hiện tại」\n"
            "👋 Thoát:        「Luna ngắt kết nối」\n"
            "```"
        ),
        inline=False
    )
    
    # Text Commands Section
    embed.add_field(
        name="⌨️ **LỆNH TEXT** (prefix: `l`)",
        value=(
            "```\n"
            "ljoin           → Vào voice channel\n"
            "lplay <bài>     → Phát bài hát\n"
            "lplay <URL>     → Phát playlist YT/Spotify\n"
            "lqueue          → Xem hàng đợi\n"
            "lnowplaying     → Bài đang phát\n"
            "lskip           → Chuyển bài\n"
            "lclear          → Xóa hàng đợi\n"
            "lstop           → Dừng & rời kênh\n"
            "```"
        ),
        inline=False
    )
    
    # Aliases Section
    embed.add_field(
        name="⚡ **SHORTCUTS**",
        value=(
            "`lp` = `lplay` • `lq` = `lqueue` • `ls` = `lskip`\n"
            "`lnp` = `lnowplaying` • `ldc` = `lstop`"
        ),
        inline=False
    )
    
    # Tips Section
    embed.add_field(
        name="💡 **TIPS**",
        value=(
            "• Nói tên bài tiếng Anh bằng **phiên âm Việt** được!\n"
            "• Thêm `remix`, `live`, `acoustic` để tìm bản khác\n"
            "• Paste link **YouTube/Spotify playlist** để thêm nhiều bài"
        ),
        inline=False
    )
    
    embed.set_footer(text="Made with 💜 for Vietnamese Discord users • v2.0")
    await ctx.send(embed=embed)


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("❌ Error: DISCORD_TOKEN not found in .env file.")
else:
    bot.run(TOKEN)
