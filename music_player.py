import yt_dlp as youtube_dl
import asyncio
import discord
import re
import os
from dotenv import load_dotenv
from english_corrector import correct_english_query, get_query_variations

# Load environment variables from .env file
load_dotenv()

# Try to import spotipy for Spotify playlist support
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    
    # Spotify API credentials - get from environment or use None
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        try:
            spotify_client = spotipy.Spotify(
                client_credentials_manager=SpotifyClientCredentials(
                    client_id=SPOTIFY_CLIENT_ID,
                    client_secret=SPOTIFY_CLIENT_SECRET
                )
            )
            # Test the connection with a simple request
            spotify_client.search(q='test', type='track', limit=1)
            SPOTIFY_AVAILABLE = True
            print("✅ Spotify API connected")
        except Exception as e:
            SPOTIFY_AVAILABLE = False
            spotify_client = None
            print(f"⚠️ Spotify API error: {e}")
    else:
        SPOTIFY_AVAILABLE = False
        spotify_client = None
        print("ℹ️ Spotify API not configured - add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env for Spotify playlist support")
        print("   Get free credentials at: https://developer.spotify.com/dashboard")
except ImportError:
    SPOTIFY_AVAILABLE = False
    spotify_client = None
    print("⚠️ spotipy not installed - run: pip install spotipy")

ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch10',  # Get 10 results to filter better
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',  # Faster search
    'nocheckcertificate': True,
    'ignoreerrors': True,  # Skip errors in search results
    'logtostderr': False,
    'geo_bypass': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['dash', 'hls']
        }
    },
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -loglevel warning -bufsize 64k -ar 48000 -ac 2'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Separate ytdl instance for extracting full info (not flat)
ytdl_full = youtube_dl.YoutubeDL({
    **ytdl_format_options,
    'extract_flat': False,
})

# 🎵 Playlist ytdl instance - allows playlist extraction
ytdl_playlist = youtube_dl.YoutubeDL({
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': False,  # Allow playlists!
    'extract_flat': True,  # Just get video URLs, don't download yet
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'geo_bypass': True,
})

# 🎵 Track currently playing song info
_current_song_info = None

def extract_spotify_playlist_id(url):
    """Extract playlist ID from Spotify URL."""
    # Matches: open.spotify.com/playlist/xxxxx or spotify.com/playlist/xxxxx
    match = re.search(r'playlist[/:]([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

async def get_spotify_tracks(playlist_url, max_tracks=100):
    """
    Get track info from Spotify playlist using Spotify API.
    Returns list of dicts with 'title' and 'artist' keys.
    """
    if not SPOTIFY_AVAILABLE or not spotify_client:
        return None
    
    playlist_id = extract_spotify_playlist_id(playlist_url)
    if not playlist_id:
        return None
    
    try:
        tracks = []
        offset = 0
        
        while len(tracks) < max_tracks:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: spotify_client.playlist_tracks(playlist_id, offset=offset, limit=50)
            )
            
            if not results or not results.get('items'):
                break
            
            for item in results['items']:
                if len(tracks) >= max_tracks:
                    break
                    
                track = item.get('track')
                if track:
                    track_name = track.get('name', '')
                    artists = track.get('artists', [])
                    artist_name = artists[0].get('name', '') if artists else ''
                    
                    if track_name:
                        tracks.append({
                            'title': track_name,
                            'artist': artist_name
                        })
            
            offset += 50
            if len(results['items']) < 50:
                break
        
        # Get playlist name
        playlist_info = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: spotify_client.playlist(playlist_id, fields='name')
        )
        playlist_name = playlist_info.get('name', 'Spotify Playlist') if playlist_info else 'Spotify Playlist'
        
        return {'name': playlist_name, 'tracks': tracks}
        
    except Exception as e:
        print(f"[SPOTIFY] Error fetching playlist: {e}")
        return None

async def search_spotify_track(query):
    """
    Search for a track on Spotify to get accurate track name + artist.
    Returns dict with 'title', 'artist', 'album', 'duration_ms' or None if not found.
    """
    if not SPOTIFY_AVAILABLE or not spotify_client:
        return None
    
    try:
        print(f"[SPOTIFY SEARCH] Searching for: {query}")
        
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: spotify_client.search(q=query, type='track', limit=5)
        )
        
        if not results or not results.get('tracks') or not results['tracks'].get('items'):
            print(f"[SPOTIFY SEARCH] No results for: {query}")
            return None
        
        tracks = results['tracks']['items']
        
        # Find best match - prefer exact matches or popular tracks
        best_track = None
        query_lower = query.lower()
        
        for track in tracks:
            track_name = track.get('name', '').lower()
            artists = [a.get('name', '') for a in track.get('artists', [])]
            artist_name = artists[0] if artists else ''
            
            # Check for close match
            if query_lower in track_name or track_name in query_lower:
                best_track = track
                break
            
            # Check if artist name is in query
            if artist_name.lower() in query_lower:
                best_track = track
                break
        
        # If no good match, use first result (usually most popular)
        if not best_track:
            best_track = tracks[0]
        
        artists = [a.get('name', '') for a in best_track.get('artists', [])]
        
        result = {
            'title': best_track.get('name', ''),
            'artist': ', '.join(artists),
            'album': best_track.get('album', {}).get('name', ''),
            'duration_ms': best_track.get('duration_ms'),
            'spotify_url': best_track.get('external_urls', {}).get('spotify', ''),
            'thumbnail': best_track.get('album', {}).get('images', [{}])[0].get('url') if best_track.get('album', {}).get('images') else None,
        }
        
        print(f"[SPOTIFY SEARCH] Found: {result['title']} - {result['artist']}")
        return result
        
    except Exception as e:
        print(f"[SPOTIFY SEARCH] Error: {e}")
        return None

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

# 🎵 Add a playlist to the queue
async def add_playlist_to_queue(ctx, playlist_url, queue, max_songs=100):
    """
    Add all songs from a YouTube/Spotify playlist to the queue.
    
    Args:
        ctx: Discord context
        playlist_url: YouTube or Spotify playlist URL
        queue: Song queue list
        max_songs: Maximum number of songs to add (default 100)
    
    Returns:
        Number of songs added
    """
    try:
        # Detect playlist type
        is_spotify = 'spotify.com' in playlist_url or 'open.spotify' in playlist_url
        is_youtube_music = 'music.youtube.com' in playlist_url
        
        if is_spotify:
            platform_name = "Spotify"
            platform_emoji = "🟢"
        elif is_youtube_music:
            platform_name = "YouTube Music"
            platform_emoji = "🔴"
        else:
            platform_name = "YouTube"
            platform_emoji = "▶️"
        
        # Send initial loading message
        loading_msg = await ctx.send(f"{platform_emoji} Đang tải {platform_name} playlist... (tối đa {max_songs} bài)")
        
        added_count = 0
        failed_count = 0
        playlist_title = "Unknown Playlist"
        tracks_to_add = []
        
        # ========== SPOTIFY PLAYLIST ==========
        if is_spotify:
            # Try Spotify API first
            spotify_data = await get_spotify_tracks(playlist_url, max_songs)
            
            if spotify_data and spotify_data.get('tracks'):
                playlist_title = spotify_data['name']
                tracks_to_add = spotify_data['tracks']
                total_tracks = len(tracks_to_add)
                
                await loading_msg.edit(content=f"{platform_emoji} Tìm thấy **{total_tracks}** bài từ **{playlist_title}**\n⏳ Đang thêm vào queue...")
                
                # LAZY LOADING: Just store search query, don't extract yet
                for idx, track in enumerate(tracks_to_add):
                    search_query = f"{track['title']} {track['artist']}".strip()
                    
                    # Store as lazy song info - will be resolved when needed
                    song_info = {
                        'lazy': True,  # Flag for lazy loading
                        'search_query': search_query,
                        'title': track['title'],
                        'uploader': track['artist'],
                        'thumbnail': None,
                        'duration': None,
                        'webpage_url': '',
                    }
                    queue.append(song_info)
                    added_count += 1
                
            else:
                if not SPOTIFY_AVAILABLE:
                    await loading_msg.edit(content="❌ **Spotify chưa được cấu hình**\n\n"
                        "📝 Để sử dụng Spotify playlist, thêm vào file `.env`:\n"
                        "```\nSPOTIFY_CLIENT_ID=your_client_id\n"
                        "SPOTIFY_CLIENT_SECRET=your_client_secret\n```\n"
                        "🔗 Lấy credentials miễn phí tại: https://developer.spotify.com/dashboard\n\n"
                        "💡 **Thay thế:** Dùng YouTube playlist hoặc `lplay <tên bài>`")
                else:
                    await loading_msg.edit(content="❌ Không thể tải Spotify playlist.\n💡 **Mẹo:** Đảm bảo playlist là public!")
                return 0
        
        # ========== YOUTUBE / YOUTUBE MUSIC PLAYLIST ==========
        else:
            # Use yt-dlp for YouTube playlists
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ytdl_playlist.extract_info(playlist_url, download=False)
            )
            
            if not info:
                await loading_msg.edit(content="❌ Không thể tải playlist. Kiểm tra lại URL.")
                return 0
            
            playlist_title = info.get('title', 'Unknown Playlist')
            entries = info.get('entries', [])
            
            if not entries:
                await loading_msg.edit(content="❌ Playlist trống hoặc không thể truy cập.")
                return 0
            
            # Filter valid entries
            valid_entries = [e for e in entries if e is not None][:max_songs]
            total_entries = len(valid_entries)
            
            await loading_msg.edit(content=f"{platform_emoji} Tìm thấy **{total_entries}** bài từ **{playlist_title}**\n⏳ Đang thêm vào queue...")
            
            # LAZY LOADING: Just store video URL/ID, don't extract full info yet
            for idx, entry in enumerate(valid_entries):
                video_url = entry.get('url') or entry.get('webpage_url')
                if not video_url:
                    video_id = entry.get('id')
                    if video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                    else:
                        failed_count += 1
                        continue
                
                # Store as lazy song info - will be resolved when needed
                song_info = {
                    'lazy': True,  # Flag for lazy loading
                    'video_url': video_url,
                    'title': entry.get('title', 'Loading...'),
                    'uploader': entry.get('uploader') or entry.get('channel') or 'Unknown',
                    'thumbnail': entry.get('thumbnail'),
                    'duration': entry.get('duration'),
                    'webpage_url': video_url,
                }
                queue.append(song_info)
                added_count += 1
        
        # ========== REPORT RESULTS ==========
        if added_count > 0:
            embed = discord.Embed(
                title=f"{platform_emoji} Playlist đã được thêm!",
                description=f"**{playlist_title}**",
                color=discord.Color.from_rgb(30, 215, 96) if is_spotify else discord.Color.red()
            )
            embed.add_field(name="✅ Đã thêm", value=f"{added_count} bài", inline=True)
            if failed_count > 0:
                embed.add_field(name="⚠️ Bỏ qua", value=f"{failed_count} bài", inline=True)
            embed.add_field(name="📊 Tổng queue", value=f"{len(queue)} bài", inline=True)
            embed.set_footer(text="⚡ Lazy loading: bài sẽ được tải khi sắp phát")
            
            # Delete loading message and send result
            await loading_msg.delete()
            await ctx.send(embed=embed)
        else:
            await loading_msg.edit(content="❌ Không thể thêm bài nào từ playlist.")
        
        return added_count
        
    except Exception as e:
        print(f"[PLAYLIST] Error: {e}")
        await ctx.send(f"❌ Lỗi khi tải playlist: {str(e)[:100]}")
        return 0

# 🔧 Resolve lazy song info - fetch full info when needed
async def resolve_lazy_song(song_info):
    """
    Resolve a lazy-loaded song to get the actual stream URL.
    Returns the resolved song_info with 'url' field, or None if failed.
    """
    if not song_info.get('lazy'):
        return song_info  # Already resolved
    
    try:
        # For Spotify songs, we need to search YouTube first
        if 'search_query' in song_info:
            search_query = song_info['search_query']
            print(f"[LAZY] Searching YouTube for: {search_query}")
            
            search_info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ytdl.extract_info(f"ytsearch1:{search_query}", download=False)
            )
            
            if search_info and search_info.get('entries') and search_info['entries'][0]:
                video_url = search_info['entries'][0].get('webpage_url') or search_info['entries'][0].get('url')
            else:
                print(f"[LAZY] No YouTube results for: {search_query}")
                return None
        else:
            video_url = song_info.get('video_url') or song_info.get('webpage_url')
        
        if not video_url:
            return None
        
        # Get full info with stream URL
        print(f"[LAZY] Extracting: {video_url}")
        video_info = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ytdl_full.extract_info(video_url, download=False)
        )
        
        if video_info and video_info.get('url'):
            # Update song_info with resolved data
            song_info['url'] = video_info['url']
            song_info['title'] = video_info.get('title', song_info.get('title', 'Unknown'))
            song_info['thumbnail'] = video_info.get('thumbnail', song_info.get('thumbnail'))
            song_info['duration'] = video_info.get('duration', song_info.get('duration'))
            song_info['uploader'] = video_info.get('uploader', song_info.get('uploader', 'Unknown'))
            song_info['webpage_url'] = video_info.get('webpage_url', video_url)
            song_info['lazy'] = False  # Mark as resolved
            return song_info
        
        return None
        
    except Exception as e:
        print(f"[LAZY] Error resolving song: {e}")
        return None

# 🎵 Add a song to the queue
async def add_to_queue(ctx, query, queue):
    original_query = query
    
    # 🟢 SPOTIFY-FIRST: Try to find exact track info on Spotify first
    spotify_track = await search_spotify_track(query)
    spotify_enhanced_query = None
    
    if spotify_track:
        # Use Spotify's exact track name + artist for more accurate YouTube search
        spotify_enhanced_query = f"{spotify_track['title']} {spotify_track['artist']}"
        await ctx.send(f"🟢 **Spotify:** {spotify_track['title']} - {spotify_track['artist']}")
        print(f"[SPOTIFY-FIRST] Using enhanced query: {spotify_enhanced_query}")
    
    # Step 1: Correct the query using english_corrector
    corrected_query = correct_english_query(query)
    
    # Get all variations to try
    query_variations = get_query_variations(query)
    
    # If we have Spotify match, prioritize that as the first search
    if spotify_enhanced_query:
        query_variations = [spotify_enhanced_query] + query_variations
    
    # Add "official audio" or "official music video" to improve search results
    enhanced_variations = []
    for v in query_variations:
        enhanced_variations.append(v)
        # Only add enhanced version if not already containing music keywords
        if not any(kw in v.lower() for kw in ['official', 'audio', 'music', 'mv', 'lyrics']):
            enhanced_variations.append(f"{v} official audio")
            enhanced_variations.append(f"{v} official music video")
    
    print(f"[SEARCH] Original: '{original_query}'")
    print(f"[SEARCH] Corrected: '{corrected_query}'")
    print(f"[SEARCH] Will try variations: {enhanced_variations[:5]}")  # Limit log
    
    last_error = None
    
    # Try each variation until one works
    for variation in enhanced_variations:
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
            
            # Handle playlist/search results
            if 'entries' in info:
                entries = [e for e in info['entries'] if e is not None]
                if not entries:
                    print(f"[SEARCH] Empty entries for '{variation}'")
                    continue
                
                # Score and rank entries to find best music video
                scored_entries = []
                for entry in entries[:15]:  # Check first 15 results
                    title = (entry.get('title') or '').lower()
                    uploader = (entry.get('uploader') or entry.get('channel') or '').lower()
                    duration = entry.get('duration') or 0
                    webpage_url = entry.get('webpage_url') or entry.get('url') or ''
                    
                    # Hard filters - skip these entirely
                    if '/shorts/' in webpage_url:
                        continue
                    if duration > 0 and duration < 60:  # Too short
                        continue
                    if duration > 7200:  # Over 2 hours
                        continue
                    
                    # Skip obvious non-music content
                    skip_keywords = [
                        'gameplay', 'gaming', 'walkthrough', 'playthrough',
                        'tutorial', 'how to', 'guide', 'tips',
                        'reaction', 'review', 'unboxing', 'haul',
                        'podcast', 'interview', 'news', 'trailer',
                        'compilation', 'moments', 'highlights', 'best of',
                        'stream', 'live stream', 'asmr', 'mukbang',
                        'funny', 'fail', 'prank', 'challenge',
                        'slowed', 'reverb', 'nightcore', '8d audio',
                        'tiktok', 'shorts', 'reels', 'clip'
                    ]
                    if any(kw in title for kw in skip_keywords):
                        continue
                    
                    # Calculate music score
                    score = 0
                    
                    # Bonus for music-related keywords in title
                    music_keywords = ['official', 'mv', 'music video', 'audio', 
                                      'lyrics', 'lyric', 'vietsub', 'engsub']
                    for kw in music_keywords:
                        if kw in title:
                            score += 20
                    
                    # Big bonus for VEVO or Topic channels (auto-generated music)
                    if 'vevo' in uploader or 'topic' in uploader:
                        score += 50
                    
                    # Bonus for official channels
                    if 'official' in uploader:
                        score += 30
                    
                    # Bonus for reasonable song duration (2-7 minutes)
                    if duration and 120 <= duration <= 420:
                        score += 15
                    elif duration and 60 <= duration <= 600:
                        score += 5
                    
                    # Penalty for very long videos
                    if duration and duration > 600:
                        score -= 10
                    
                    # Small bonus if query words appear in title
                    query_words = variation.lower().split()
                    matches = sum(1 for w in query_words if w in title and len(w) > 2)
                    score += matches * 5
                    
                    # BIG bonus if title contains the EXACT original query
                    # This ensures Vietnamese songs like "chúng ta của hiện tại" are prioritized
                    if original_query.lower() in title:
                        score += 100  # Strong preference for exact matches
                    
                    # 🎵 Remix penalty: penalize remixes unless user specifically wants one
                    remix_keywords = ['remix', 'rmx', 'bootleg', 'mashup', 'edit', 'flip', 'rework']
                    user_wants_remix = any(kw in original_query.lower() for kw in remix_keywords)
                    title_is_remix = any(kw in title for kw in remix_keywords)
                    
                    if title_is_remix and not user_wants_remix:
                        score -= 80  # Strong penalty for remixes when user wants original
                    elif title_is_remix and user_wants_remix:
                        score += 50  # Bonus if user wants remix and this is a remix
                    
                    scored_entries.append((entry, score))
                
                if not scored_entries:
                    print(f"[SEARCH] No valid music video found for '{variation}'")
                    continue
                
                # Sort by score and pick best
                scored_entries.sort(key=lambda x: x[1], reverse=True)
                best_entry, best_score = scored_entries[0]
                print(f"[SEARCH] Best match: {best_entry.get('title')} (score: {best_score})")
                
                # Extract full info for the best entry
                video_url = best_entry.get('webpage_url') or best_entry.get('url')
                if not video_url:
                    continue
                
                info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda u=video_url: ytdl_full.extract_info(u, download=False)
                )
                
                if info is None:
                    continue
            
            # Validate the final result has a playable URL
            if not info.get('url'):
                print(f"[SEARCH] No playable URL for: {info.get('title')}")
                continue
            
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
            if variation != original_query and variation.replace(' official audio', '') != original_query:
                await ctx.send(f"🔍 Đã tìm: **{corrected_query}** (từ '{original_query}')")
            
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
    
    # 🔧 LAZY LOADING: Resolve lazy songs before playing
    if song_info.get('lazy'):
        loading_embed = discord.Embed(
            title="⏳ Đang tải bài tiếp theo...",
            description=f"**{song_info.get('title', 'Loading...')}**",
            color=discord.Color.orange()
        )
        loading_msg = await ctx.send(embed=loading_embed)
        
        resolved = await resolve_lazy_song(song_info)
        
        if not resolved or not resolved.get('url'):
            await loading_msg.edit(embed=discord.Embed(
                title="❌ Không thể tải bài hát",
                description=f"**{song_info.get('title', 'Unknown')}**\nĐang chuyển sang bài tiếp theo...",
                color=discord.Color.red()
            ))
            # Try next song
            await asyncio.sleep(2)
            await loading_msg.delete()
            await start_playback(ctx, queue)
            return
        
        song_info = resolved
        await loading_msg.delete()
    
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
        description=f"**[{song_info['title']}]({song_info.get('webpage_url', '')})**",
        color=discord.Color.from_rgb(255, 0, 127)  # Pink color
    )
    if song_info.get('thumbnail'):
        embed.set_thumbnail(url=song_info['thumbnail'])
    embed.add_field(name="👤 Nghệ sĩ", value=song_info.get('uploader', 'Unknown'), inline=True)
    embed.add_field(name="⏱️ Thời lượng", value=format_duration(song_info.get('duration')), inline=True)
    
    # Show queue info
    if queue:
        embed.set_footer(text=f"📋 Còn {len(queue)} bài trong queue")
    else:
        embed.set_footer(text="🎧 Nói 'thêm bài' để thêm nhạc")
    
    await ctx.send(embed=embed)
