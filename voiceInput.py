import wave
import speech_recognition as sr
from discord.ext import voice_recv
import asyncio
import audioop
import time
import threading

# Global queue for recognized text
text_queue = asyncio.Queue()

# ============================================
# CONFIGURATION - Điều chỉnh tại đây
# ============================================
DEBUG_MODE = False  # Tắt debug messages để giảm spam
DEBUG_INTERVAL = 30  # Chỉ hiện debug mỗi 30 giây (nếu DEBUG_MODE = True)
SILENCE_THRESHOLD = 1.5  # Thời gian im lặng trước khi xử lý (giây)
MIN_AUDIO_LENGTH = 0.8  # Độ dài tối thiểu của audio để xử lý (giây)
RMS_THRESHOLD = 50  # Ngưỡng âm lượng để nhận voice (tăng lên để bỏ qua tiếng ồn nhỏ)
WAKE_WORDS = ["luna", "lu na", "lú na", "lủ na"]  # Từ khóa kích hoạt

class DiscordSink(voice_recv.AudioSink):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.buffers = {}  # user_id -> bytearray
        self.last_speak_time = {}  # user_id -> time
        self.recognizer = sr.Recognizer()
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.write_counter = 0
        self.last_debug_time = time.time()
        
        # Tracking để giảm spam
        self.processing_count = 0
        self.last_process_time = {}  # user_id -> time (để rate limit)
        self.pending_users = set()  # Users đang được xử lý
        
        self.bot.loop.create_task(self.check_silence())
        
    def wants_opus(self):
        return False  # Request PCM data

    async def check_silence(self):
        while True:
            await asyncio.sleep(0.2)  # Tăng từ 0.1 lên 0.2 để giảm tải CPU
            try:
                current_time = time.time()
                users_to_process = []
                
                with self.lock:
                    for user, buffer in list(self.buffers.items()):
                        if len(buffer) > 0:
                            silence_duration = current_time - self.last_speak_time.get(user, 0)
                            
                            # Chỉ xử lý nếu đủ im lặng và user chưa đang được xử lý
                            if silence_duration > SILENCE_THRESHOLD and user not in self.pending_users:
                                # Rate limit: không xử lý user quá thường xuyên
                                last_process = self.last_process_time.get(user, 0)
                                if current_time - last_process > 2.0:  # Tối thiểu 2 giây giữa các lần xử lý
                                    users_to_process.append(user)
                    
                    for user in users_to_process:
                        if len(self.buffers[user]) > 0:
                            audio_data = bytes(self.buffers[user])
                            self.buffers[user] = bytearray()
                            self.pending_users.add(user)
                            self.last_process_time[user] = current_time
                            
                            # Chỉ log nếu DEBUG_MODE bật
                            if DEBUG_MODE:
                                print(f"[Voice] Processing audio from user (silence timeout)")
                            
                            self.bot.loop.create_task(self.process_audio(audio_data, user))
                            
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[Voice] Silence checker error: {e}")

    def write(self, user, data):
        if user is None:
            return

        # Debug mỗi DEBUG_INTERVAL giây thay vì liên tục
        if DEBUG_MODE:
            self.write_counter += 1
            current_time = time.time()
            if current_time - self.last_debug_time > DEBUG_INTERVAL:
                print(f"[Voice] Received {self.write_counter} audio packets in last {DEBUG_INTERVAL}s")
                self.write_counter = 0
                self.last_debug_time = current_time

        with self.lock:
            if user not in self.buffers:
                self.buffers[user] = bytearray()
                self.last_speak_time[user] = time.time()

            try:
                rms = audioop.rms(data.pcm, 2)
            except Exception as e:
                return  # Bỏ qua lỗi RMS thay vì log

            # Tăng ngưỡng RMS để bỏ qua tiếng ồn nhỏ
            if rms > RMS_THRESHOLD:
                self.buffers[user].extend(data.pcm)
                self.last_speak_time[user] = time.time()
            else:
                silence_duration = time.time() - self.last_speak_time[user]
                
                # Vẫn thêm audio nếu đang trong quá trình nói (để không cắt giữa chừng)
                if user in self.buffers and len(self.buffers[user]) > 0 and silence_duration < SILENCE_THRESHOLD:
                    self.buffers[user].extend(data.pcm)

    async def process_audio(self, pcm_data, user=None):
        """Xử lý audio và nhận dạng giọng nói"""
        try:
            # Kiểm tra độ dài tối thiểu
            min_bytes = int(48000 * 2 * MIN_AUDIO_LENGTH)
            if len(pcm_data) < min_bytes:
                return  # Quá ngắn, bỏ qua

            try:
                mono_data = audioop.tomono(pcm_data, 2, 0.5, 0.5)
            except Exception as e:
                return

            audio = sr.AudioData(mono_data, 48000, 2)

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
                except Exception:
                    return None
            
            # Chạy cả 2 ngôn ngữ song song
            vi_task = asyncio.create_task(try_recognize("vi-VN"))
            en_task = asyncio.create_task(try_recognize("en-US"))
            
            vi_result, en_result = await asyncio.gather(vi_task, en_task)
            
            # Xác định kết quả
            final_text = None
            
            if vi_result and en_result:
                # Ưu tiên tiếng Việt cho các lệnh điều khiển
                vi_commands = ["luna", "chuyển bài", "ngắt kết nối", "bài hiện tại", "ngắt", "kết nối"]
                is_vi_command = any(cmd in vi_result for cmd in vi_commands)
                
                if is_vi_command:
                    final_text = vi_result
                else:
                    # Cho bài hát, ưu tiên tiếng Anh
                    final_text = en_result if len(en_result) >= len(vi_result) * 0.7 else vi_result
                    
            elif vi_result:
                final_text = vi_result
            elif en_result:
                final_text = en_result
            
            # Chỉ đưa vào queue nếu có kết quả và chứa wake word hoặc là lệnh quan trọng
            if final_text:
                important_commands = ["chuyển bài", "ngắt kết nối", "bài hiện tại"]
                
                # Kiểm tra xem có phải là nội dung quan trọng không
                contains_wake_word = any(wake in final_text for wake in WAKE_WORDS)
                contains_command = any(cmd in final_text for cmd in important_commands)
                
                if contains_wake_word or contains_command:
                    print(f"[Voice] ✅ Recognized: {final_text}")
                    await text_queue.put(final_text)
                else:
                    # Không phải lệnh quan trọng -> bỏ qua (không spam)
                    if DEBUG_MODE:
                        print(f"[Voice] Ignored (no wake word): {final_text}")
                        
        except Exception as e:
            if DEBUG_MODE:
                print(f"[Voice] Error: {e}")
        finally:
            # Xóa user khỏi pending sau khi xử lý xong
            if user:
                with self.lock:
                    self.pending_users.discard(user)

    def cleanup(self):
        pass

def setup_sink(voice_client, bot):
    sink = DiscordSink(bot)
    voice_client.listen(sink)
    return sink

async def get_next_phrase():
    return await text_queue.get()
