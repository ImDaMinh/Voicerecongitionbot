import wave
import speech_recognition as sr
from discord.ext import voice_recv
import asyncio
import audioop
import time
import threading

# Global queue for recognized text
text_queue = asyncio.Queue()

class DiscordSink(voice_recv.AudioSink):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.buffers = {}  # user_id -> bytearray
        self.last_speak_time = {} # user_id -> time
        self.recognizer = sr.Recognizer()
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.write_counter = 0  # Debug counter
        self.last_debug_time = time.time()  # For periodic debug output
        self.bot.loop.create_task(self.check_silence())
        
    def wants_opus(self):
        return False # Request PCM data

    async def check_silence(self):
        while True:
            await asyncio.sleep(0.1)
            try:
                current_time = time.time()
                users_to_process = []
                
                with self.lock:
                    for user, buffer in self.buffers.items():
                        if len(buffer) > 0:
                            silence_duration = current_time - self.last_speak_time.get(user, 0)
                            if silence_duration > 1.2:
                                users_to_process.append(user)
                    
                    for user in users_to_process:
                        if len(self.buffers[user]) > 0:
                            print(f"DEBUG: Silence timeout for {user} (Background)")
                            audio_data = bytes(self.buffers[user])
                            self.buffers[user] = bytearray()
                            # We are already on the loop, so call directly? 
                            # No, process_audio is async, so we await it.
                            # But we are holding the lock! We shouldn't await while holding lock if process_audio takes time.
                            # process_audio does I/O (save file) and blocking calls (recognize_google in executor).
                            # So we should NOT await it inside the lock.
                            
                            # Schedule it to run on the loop (fire and forget from the lock's perspective)
                            self.bot.loop.create_task(self.process_audio(audio_data))
                            
            except Exception as e:
                print(f"DEBUG: Silence checker error: {e}")

    def write(self, user, data):
        if user is None:
            return

        # Debug: Track if write is still being called
        self.write_counter += 1
        current_time = time.time()
        if current_time - self.last_debug_time > 5:
            print(f"[SINK DEBUG] write() called {self.write_counter} times in last 5 seconds - SINK ALIVE")
            self.write_counter = 0
            self.last_debug_time = current_time

        with self.lock:
            if user not in self.buffers:
                self.buffers[user] = bytearray()
                self.last_speak_time[user] = time.time()

            try:
                rms = audioop.rms(data.pcm, 2)
            except Exception as e:
                print(f"DEBUG: RMS Error: {e}")
                return

            if rms > 30: 
                 self.buffers[user].extend(data.pcm)
                 self.last_speak_time[user] = time.time()
            else:
                 silence_duration = time.time() - self.last_speak_time[user]
                 
                 if user in self.buffers and len(self.buffers[user]) > 0:
                     self.buffers[user].extend(data.pcm)
                 
                 # We still keep this check here for immediate processing if packets are still flowing
                 if silence_duration > 1.2 and len(self.buffers[user]) > 0:
                     print(f"DEBUG: Processing phrase for {user}, length: {len(self.buffers[user])} (Write)")
                     audio_data = bytes(self.buffers[user])
                     self.buffers[user] = bytearray() 
                     
                     asyncio.run_coroutine_threadsafe(self.process_audio(audio_data), self.bot.loop)

    async def process_audio(self, pcm_data):
        # ... (rest of the method is same, just need to make sure indentation is correct)
        print(f"DEBUG: Starting recognition on {len(pcm_data)} bytes")
        if len(pcm_data) < 48000 * 2 * 0.5: 
            print("DEBUG: Clip too short")
            return

        try:
            mono_data = audioop.tomono(pcm_data, 2, 0.5, 0.5)
        except Exception as e:
            print(f"[Voice] Audio conversion error: {e}")
            return
        
        try:
            with wave.open("debug_last_phrase.wav", "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(48000)
                f.writeframes(mono_data)
            print("DEBUG: Saved debug_last_phrase.wav")
        except Exception as e:
            print(f"DEBUG: Failed to save wav: {e}")

        audio = sr.AudioData(mono_data, 48000, 2)

        try:
            print("DEBUG: Sending to Google (both VI and EN in parallel)...")
            
            # Run both recognitions in parallel
            loop = asyncio.get_event_loop()
            
            async def try_recognize(lang):
                try:
                    result = await loop.run_in_executor(
                        None, 
                        lambda: self.recognizer.recognize_google(audio, language=lang)
                    )
                    return result.strip().lower() if result else None
                except sr.UnknownValueError:
                    return None
                except Exception as e:
                    print(f"DEBUG: Recognition error ({lang}): {e}")
                    return None
            
            # Run both languages in parallel
            vi_task = asyncio.create_task(try_recognize("vi-VN"))
            en_task = asyncio.create_task(try_recognize("en-US"))
            
            vi_result, en_result = await asyncio.gather(vi_task, en_task)
            
            print(f"DEBUG: VI result: '{vi_result}', EN result: '{en_result}'")
            
            # Choose the best result
            final_text = None
            
            if vi_result and en_result:
                # Both succeeded - choose based on content
                # Prefer Vietnamese for Vietnamese commands
                vi_commands = ["luna", "chuyển bài", "ngắt kết nối", "bài hiện tại", "ngắt", "kết nối", "hiển thị"]
                
                # Check if Vietnamese result contains Vietnamese commands
                is_vi_command = any(cmd in vi_result for cmd in vi_commands)
                
                if is_vi_command:
                    final_text = vi_result
                    print(f"[Voice] Recognized (VI preferred - command): {final_text}")
                else:
                    # For song names, prefer English (usually more accurate for song titles)
                    # But use Vietnamese if it looks like a Vietnamese song/command
                    if len(en_result) >= len(vi_result) * 0.7:  # English is at least 70% as long
                        final_text = en_result
                        print(f"[Voice] Recognized (EN preferred - song): {final_text}")
                    else:
                        final_text = vi_result
                        print(f"[Voice] Recognized (VI): {final_text}")
                        
            elif vi_result:
                final_text = vi_result
                print(f"[Voice] Recognized (VI only): {final_text}")
            elif en_result:
                final_text = en_result
                print(f"[Voice] Recognized (EN only): {final_text}")
            else:
                print("DEBUG: Could not understand audio in either language")
            
            if final_text:
                await text_queue.put(final_text)
                
        except Exception as e:
            print(f"[Voice] Error: {e}")

    def cleanup(self):
        pass

def setup_sink(voice_client, bot):
    sink = DiscordSink(bot)
    voice_client.listen(sink)
    return sink

async def get_next_phrase():
    return await text_queue.get()

