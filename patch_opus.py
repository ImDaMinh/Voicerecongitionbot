import discord.ext.voice_recv.opus as recv_opus
import logging

# Monkey patch to suppress OpusError: corrupted stream
# The class is PacketDecoder, not Decoder
original_decode_packet = recv_opus.PacketDecoder._decode_packet

def patched_decode_packet(self, packet):
    try:
        return original_decode_packet(self, packet)
    except Exception as e:
        # print(f"[WARNING] Opus decode error: {e}")
        # Return empty PCM data (silence)
        # 3840 bytes = 960 samples * 2 channels * 2 bytes/sample (20ms)
        return packet, b'\x00' * 3840 

recv_opus.PacketDecoder._decode_packet = patched_decode_packet
print("✅ Applied Opus error patch (PacketDecoder)")
