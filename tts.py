import asyncio
import os
import tempfile
import hashlib

from playsound import playsound
import edge_tts


DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
# 提升语速以减少响应时间（原为 -10%）
DEFAULT_RATE = "+20%"

# 语音缓存目录（避免重复网络合成）
SPEECH_CACHE_DIR = os.path.join(tempfile.gettempdir(), "voice_cache")
os.makedirs(SPEECH_CACHE_DIR, exist_ok=True)


def _cache_path(text: str, voice: str, rate: str) -> str:
    key = f"{voice}|{rate}|{text}".encode("utf-8")
    name = hashlib.sha1(key).hexdigest() + ".mp3"
    return os.path.join(SPEECH_CACHE_DIR, name)


async def _synth_to_mp3(text: str, out_path: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> str:
    """合成语音到指定MP3文件，返回文件路径。"""
    comm = edge_tts.Communicate(text, voice=voice, rate=rate)
    await comm.save(out_path)
    return out_path


def speak(text: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> None:
    """合成并播放中文语音：
    - 优先使用缓存，显著降低延迟
    - 播放采用非阻塞模式，避免卡住主流程
    """
    try:
        mp3_path = _cache_path(text, voice, rate)
        if not os.path.exists(mp3_path):
            # 未缓存时进行合成（一次性网络请求），后续复用
            asyncio.run(_synth_to_mp3(text=text, out_path=mp3_path, voice=voice, rate=rate))
        # 非阻塞播放，提升交互响应速度
        playsound(mp3_path, block=False)
    except Exception:
        # 避免语音异常导致程序中断
        pass