import os
import json
from typing import Iterator, Optional, List

import sounddevice as sd
from vosk import Model, KaldiRecognizer


DEFAULT_MODEL_DIR = os.getenv("VOSK_MODEL_DIR", os.path.join("models", "vosk-model-small-cn-0.22"))


class STT:
    """简单的中文语音识别（Vosk），返回识别到的完整句子。"""

    def __init__(self, model_dir: Optional[str] = None, samplerate: int = 16000, grammar_words: Optional[List[str]] = None) -> None:
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.samplerate = samplerate
        self._model: Optional[Model] = None
        self._grammar_words = grammar_words

    def available(self) -> bool:
        return os.path.isdir(self.model_dir)

    def _ensure_model(self) -> None:
        if self._model is None:
            self._model = Model(self.model_dir)

    def listen(self) -> Iterator[str]:
        """开启麦克风，持续返回识别到的文本（去除空格）。"""
        self._ensure_model()
        assert self._model is not None

        # 如果提供了受限词表，则启用语法模式以提升识别准确度
        if self._grammar_words:
            grammar = json.dumps(self._grammar_words, ensure_ascii=False)
            rec = KaldiRecognizer(self._model, self.samplerate, grammar)
        else:
            rec = KaldiRecognizer(self._model, self.samplerate)
        rec.SetWords(True)

        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, dtype="int16", channels=1) as stream:
            while True:
                chunk, _ = stream.read(8000)
                # 确保传递给Vosk的是bytes而不是memoryview/cffi buffer
                data = bytes(chunk)
                if len(data) == 0:
                    continue
                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    try:
                        obj = json.loads(result)
                        raw = obj.get("text", "")
                        # 规范化常见误识：把->百、意->一、O/〇->零、两->二 等
                        text = normalize_stt_text(raw)
                        yield text
                    except Exception:
                        pass
                else:
                    # PartialResult 可忽略，等完整句子
                    pass


def normalize_stt_text(text: str) -> str:
    """对STT文本进行中文数字相关的纠正与规范化。"""
    t = text.strip().replace(" ", "")
    # 常见混淆替换
    replacements = {
        # 数字相关纠错
        "把": "百",  # 一把二十 -> 一百二十
        "意": "一",  # 意百度 -> 一百度
        "本": "百",  # 二本四十 -> 二百四十
        "而": "二",  # 而速度 -> 二速度
        "尔": "二",  # 尔百度 -> 二百度
        "儿": "二",  # 儿十度 -> 二十度
        "是": "十",  # 一是二 -> 一十二（在数字上下文中）
        "实": "十",  # 二实度 -> 二十度
        "石": "十",  # 一石八 -> 一十八
        "拾": "十",  # 二拾度 -> 二十度
        "〇": "零",
        "O": "零",
        "o": "零",
        "两": "二",
        "俩": "二",
        
        # 水果名近音修正
        "习惯": "西瓜",
        "压力": "鸭梨",
        "雅力": "鸭梨",
        "牙梨": "鸭梨",
        "鸭离": "鸭梨",
        "西刮": "西瓜",
        "西官": "西瓜",
        "西关": "西瓜",
        "苹果": "苹果",  # 确保正确
        "平果": "苹果",
        "评果": "苹果",
        
        # 常用词纠错
        "我说": "我说",  # 确保正确
        "握手": "我说",
        "我收": "我说",
        "度": "度",  # 确保正确
        "读": "度",
        "毒": "度",
        "独": "度",
    }
    # 先进行基础替换
    for k, v in replacements.items():
        t = t.replace(k, v)
    
    # 特殊处理：修复常见的数字识别错误模式
    import re
    
    # 处理 "一八二十六" -> "一百八十六" 这类模式
    # 匹配 "数字+八+数字+十+数字" 的模式
    pattern1 = re.compile(r'([一二三四五六七八九])八([一二三四五六七八九]?)十([一二三四五六七八九]?)')
    t = pattern1.sub(r'\1百八十\3', t)
    
    # 处理 "一八二十" -> "一百八十" 这类模式
    pattern2 = re.compile(r'([一二三四五六七八九])八([一二三四五六七八九]?)十')
    t = pattern2.sub(r'\1百八十', t)
    
    # 处理 "一八二" -> "一百八十二" 这类模式（当后面跟度时）
    pattern3 = re.compile(r'([一二三四五六七八九])八([一二三四五六七八九])度')
    t = pattern3.sub(r'\1百八\2度', t)
    
    # 处理 "二四零" -> "二百四十" 这类模式
    pattern4 = re.compile(r'([一二三四五六七八九])([一二三四五六七八九])零度')
    t = pattern4.sub(r'\1百\2十度', t)
    
    return t