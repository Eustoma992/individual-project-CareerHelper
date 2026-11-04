# -*- coding: utf-8 -*-
"""语音能力模块：
- transcribe(): 录音转文字（本地 faster-whisper，中文，无需上传第三方）
- tts(): 问题朗读（edge-tts，微软语音，返回 mp3 字节）
两个函数都做了懒加载与异常上抛，由页面层决定降级方式。
"""
import asyncio
import io
import os
import re

# HuggingFace 官方源在国内可能不可达，优先走镜像；必须在 import faster_whisper 之前设置
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_MODEL = None
# 中文识别质量与速度的平衡；云端内存紧张时可设 WHISPER_MODEL=base / tiny
_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
# 项目内置模型目录（models/faster-whisper-small），存在则直接加载，避免联网下载
_LOCAL_MODEL_DIR = os.getenv(
    "JOBPREP_WHISPER_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "models", "faster-whisper-small"),
)


def _get_model():
    """懒加载 whisper 模型（进程内单例，多次模拟面试不重复加载）。"""
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        # 本地有完整模型就离线加载，否则按模型名从 HuggingFace 缓存/下载
        source = _LOCAL_MODEL_DIR if os.path.isfile(os.path.join(_LOCAL_MODEL_DIR, "model.bin")) else _MODEL_NAME
        _MODEL = WhisperModel(source, device=_DEVICE, compute_type=_COMPUTE_TYPE)
    return _MODEL


def _decode(audio_bytes):
    """把录音字节流解码为 16kHz 单声道 float32 波形（soundfile 自带 libsndfile，支持 wav/mp3/ogg）。"""
    import io

    import numpy as np
    import soundfile as sf

    data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    target = 16000
    if sr != target and len(mono):
        if sr % target == 0 and sr > target:      # 48k/32k 等整数倍：块平均降采样
            k = sr // target
            n = len(mono) // k * k
            mono = mono[:n].reshape(-1, k).mean(axis=1)
        else:                                      # 非整数倍：线性插值
            idx = np.linspace(0, len(mono) - 1, int(len(mono) * target / sr))
            mono = np.interp(idx, np.arange(len(mono)), mono).astype("float32")
    return mono.astype("float32")


def _tidy(text):
    """把中文语境里的半角标点规范为全角，读起来更像成稿。"""
    text = text.strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff]),(?!\d)", "，", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\.(?!\d)", "。", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\?", "？", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])!", "！", text)
    return text


def transcribe(audio_bytes, suffix="wav"):
    """把录音字节流转写为中文文本。失败抛异常，由调用方提示。"""
    model = _get_model()
    try:
        audio = _decode(audio_bytes)
    except Exception as e:
        raise RuntimeError(f"录音无法解码（可能为空或格式异常），请重新录音：{e}") from e
    if audio.size == 0:
        return ""
    segments, _info = model.transcribe(audio, language="zh", vad_filter=True,
                                       beam_size=5)
    return _tidy("".join(s.text for s in segments))


def tts(text, voice="zh-CN-XiaoxiaoNeural"):
    """把文本合成为 mp3 音频字节（用于朗读面试官的问题）。"""
    import edge_tts

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    return asyncio.run(_run())
